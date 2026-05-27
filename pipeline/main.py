"""
Pipeline tự động tạo + upload 1 video YouTube Shorts mỗi ngày.
Kênh: Tài Chính 5 Phút

Flow: ideas.json -> LOAD pre-generated script (data/scripts/{id}.json)
   -> Pexels clips -> Google TTS WaveNet voice
   -> FFmpeg ghép video -> YouTube upload -> log published.json

Script được Claude (qua Cowork/Code) generate sẵn và commit lên repo.
Pipeline KHÔNG gọi LLM API → không phụ thuộc Groq/OpenAI/Anthropic.

Chạy bởi: GitHub Actions cron daily.yml
"""

import asyncio
import json
import os
import random
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy.editor import (AudioFileClip, CompositeAudioClip,
                            CompositeVideoClip, TextClip, VideoFileClip,
                            concatenate_videoclips)

# Fix Pillow 10+ compat: ANTIALIAS bi xoa, MoviePy 1.0.3 van dung
from PIL import Image as _PILImage
if not hasattr(_PILImage, "ANTIALIAS"):
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

# Fix MoviePy khong tu tim duoc ImageMagick (cross-platform: Linux/Mac/Windows)
import shutil as _shutil
import platform as _platform
import glob as _glob
from moviepy.config import change_settings as _change_settings

_is_win = _platform.system() == "Windows"

# Uu tien env var (test_local.py / GitHub Actions set san)
_imagemagick_path = os.environ.get("IMAGEMAGICK_BINARY", "")

if not _imagemagick_path:
    # Tim 'magick' (IMv7) truoc — chinh xac va an toan tren moi OS
    _imagemagick_path = _shutil.which("magick") or ""

if not _imagemagick_path and not _is_win:
    # Linux/Mac: 'convert' la safe alias cua ImageMagick
    _imagemagick_path = (
        _shutil.which("convert")
        or _shutil.which("convert-im6.q16")
        or "/usr/bin/convert"
    )

if not _imagemagick_path and _is_win:
    # Windows: 'convert.exe' o System32 KHONG PHAI ImageMagick — phai tim trong install dir
    for _pattern in [
        r"C:\Program Files\ImageMagick-*\magick.exe",
        r"C:\Program Files (x86)\ImageMagick-*\magick.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\ImageMagick\magick.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\ImageMagick.ImageMagick*\magick.exe"),
    ]:
        _matches = _glob.glob(_pattern)
        if _matches:
            _imagemagick_path = _matches[0]
            break

_change_settings({"IMAGEMAGICK_BINARY": _imagemagick_path or "magick"})
print(f"[init] ImageMagick: {_imagemagick_path or '(default: magick)'}")

# ==================== CONFIG ====================
# NOTE: GROQ_API_KEY đã bỏ — pipeline đọc script từ data/scripts/{id}.json
# (Claude qua Cowork generate sẵn và commit lên repo)
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
GOOGLE_TTS_KEY = os.environ.get("GOOGLE_TTS_API_KEY", "")
# YT vars: LAZY — chi can khi upload_to_youtube() (test_local.py khong can)
YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN", "")

def _require_env(name, value):
    if not value:
        raise RuntimeError(
            f"Missing env var: {name}. Set in shell or .env file before running."
        )

REPO_ROOT = Path(__file__).resolve().parent.parent
IDEAS_FILE = REPO_ROOT / "data" / "ideas.json"
PUBLISHED_FILE = REPO_ROOT / "data" / "published.json"
SCRIPTS_DIR = REPO_ROOT / "data" / "scripts"  # Thu muc chua script JSON pre-gen
BGM_DIR = REPO_ROOT / "audio"  # Folder chua background music (.mp3)

# Xoay vòng 2 voice NAM Google WaveNet cho de-templating
VOICES = [
    "vi-VN-Wavenet-B",  # Male 1 - nam trẻ, trung tính
    "vi-VN-Wavenet-D",  # Male 2 - nam trầm, mature
]

# Disclaimer YMYL bắt buộc (Finance niche)
DISCLAIMER_TEXT = ("⚠️ Video chỉ mang tính giáo dục, KHÔNG phải lời khuyên "
                   "đầu tư. Hãy tham khảo chuyên gia tài chính.")

# ==================== STEP 1: LẤY Ý TƯỞNG ====================
def pick_next_idea():
    """Lấy idea đầu tiên có status='todo' từ ideas.json."""
    with open(IDEAS_FILE, "r", encoding="utf-8") as f:
        ideas = json.load(f)
    todo = [i for i in ideas if i.get("status") == "todo"]
    if not todo:
        print("Het y tuong! Vui long them moi vao ideas.json")
        sys.exit(0)
    picked = todo[0]
    print(f"[1/7] Picked idea #{picked['id']}: {picked['title']}")
    return picked, ideas

def mark_published(ideas, idea_id, video_id):
    """Mark idea đã đăng, append vào published.json."""
    for i in ideas:
        if i["id"] == idea_id:
            i["status"] = "published"
            i["video_id"] = video_id
            i["published_at"] = datetime.now(timezone.utc).isoformat()
    with open(IDEAS_FILE, "w", encoding="utf-8") as f:
        json.dump(ideas, f, ensure_ascii=False, indent=2)
    # Append published log
    log = []
    if PUBLISHED_FILE.exists():
        with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    log.append({
        "idea_id": idea_id,
        "video_id": video_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

# ==================== STEP 2: LOAD SCRIPT (PRE-GENERATED BY CLAUDE) ====================
def load_script(idea):
    """Doc script JSON da pre-generate boi Claude (qua Cowork) tu data/scripts/{id}.json.

    Script duoc tao thu cong va commit len repo -> khong phu thuoc LLM API.
    Format chuan: title, description, tags, scenes[8] = {voiceover, visual_keyword}.
    """
    idea_id = idea["id"]
    script_path = SCRIPTS_DIR / f"{idea_id}.json"

    if not script_path.exists():
        raise FileNotFoundError(
            f"Script chua duoc generate cho idea {idea_id}: {script_path}\n"
            f"=> Mo Cowork va bao: 'Gen script cho idea {idea_id}' "
            f"hoac chay manual rooi commit file vao data/scripts/."
        )

    with open(script_path, encoding="utf-8") as f:
        data = json.load(f)

    # Validate schema
    required = ["title", "description", "tags", "scenes"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Script {script_path} thieu field bat buoc: {missing}")

    if not isinstance(data["scenes"], list) or len(data["scenes"]) < 6:
        raise ValueError(
            f"Script {script_path}: scenes phai la list >=6 phan tu "
            f"(co {len(data.get('scenes', []))})"
        )

    for i, sc in enumerate(data["scenes"]):
        if "voiceover" not in sc or "visual_keyword" not in sc:
            raise ValueError(
                f"Script {script_path} scene {i}: thieu voiceover hoac visual_keyword"
            )

    print(f"[2/7] Loaded pre-generated script: {data['title']}")
    print(f"      Source: {script_path.name}")
    print(f"      Scenes: {len(data['scenes'])}")
    return data


# Backward compat: workflow cu/test goi generate_script() -> redirect sang load_script()
def generate_script(idea):
    return load_script(idea)

# ==================== STEP 3: TẢI PEXELS CLIPS ====================
def download_pexels_clip(keyword, output_path):
    """Tải 1 video vertical từ Pexels theo keyword. Random 1/5 kết quả."""
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_KEY},
        params={
            "query": keyword,
            "orientation": "portrait",
            "size": "large",
            "per_page": 5,
        },
        timeout=30,
    )
    r.raise_for_status()
    videos = r.json().get("videos", [])
    if not videos:
        # Fallback: search rộng hơn
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": "business", "orientation": "portrait", "per_page": 5},
            timeout=30,
        )
        videos = r.json().get("videos", [])

    chosen = random.choice(videos)
    # Tìm file HD vertical
    video_files = sorted(chosen["video_files"],
                         key=lambda f: f.get("width", 0))
    target = next((f for f in video_files if f.get("width", 0) >= 1080), video_files[-1])

    resp = requests.get(target["link"], stream=True, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

def fetch_all_clips(scenes, tmpdir):
    """Tai toan bo clip CONCURRENT - 8 thread song song -> tiet kiem 20s."""
    print(f"[3/7] Downloading {len(scenes)} clips concurrently...")

    def fetch_one(idx_scene):
        i, scene = idx_scene
        path = Path(tmpdir) / f"clip_{i}.mp4"
        kw = scene["visual_keyword"]
        try:
            download_pexels_clip(kw, path)
            return (i, path, kw, None)
        except Exception as e:
            try:
                download_pexels_clip("business meeting", path)
                return (i, path, kw, f"fallback: {e}")
            except Exception as e2:
                return (i, None, kw, str(e2))

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(fetch_one, enumerate(scenes)))

    paths = [None] * len(scenes)
    for i, path, kw, err in sorted(results, key=lambda x: x[0]):
        status = "OK" if not err else f"WARN ({err[:40]})"
        print(f"      Clip {i+1}/{len(scenes)}: '{kw}' -> {status}")
        paths[i] = path
    return paths

# ==================== STEP 4: SINH VOICE (GOOGLE CLOUD TTS WAVENET) ====================
import base64

def generate_voice_per_scene(script_data, tmpdir):
    """Sinh voice cho TUNG SCENE rieng -> caption sync chinh xac voi voice."""
    voice_name = VOICES[datetime.now().day % len(VOICES)]
    print(f"[4/7] Generating voice per scene ({voice_name})...")
    scene_paths = []
    for i, scene in enumerate(script_data["scenes"]):
        text = scene["voiceover"].strip()
        path = Path(tmpdir) / f"voice_{i}.mp3"
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_KEY}"
        body = {
            "input": {"text": text},
            "voice": {"languageCode": "vi-VN", "name": voice_name},
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.15,  # +15% nhanh hon binh thuong (Shorts cu)
                "pitch": 0.0,
                "volumeGainDb": 2.0,
                "sampleRateHertz": 24000,
                "effectsProfileId": ["small-bluetooth-speaker-class-device"],
            },
        }
        r = requests.post(url, json=body, timeout=60)
        if r.status_code != 200:
            print(f"      TTS API error scene {i+1}: {r.status_code} - {r.text[:200]}")
            r.raise_for_status()
        audio_bytes = base64.b64decode(r.json()["audioContent"])
        with open(path, "wb") as f:
            f.write(audio_bytes)
        scene_paths.append(path)
    print(f"      Generated {len(scene_paths)} voice files")
    return scene_paths


# Backward compat name
def generate_voice(script_data, tmpdir):
    return generate_voice_per_scene(script_data, tmpdir)

# ==================== STEP 5: GHÉP VIDEO (MOVIEPY) ====================
def assemble_video(clip_paths, scene_voice_paths, script_data, tmpdir):
    """Ghep clip + voice per scene + caption SYNC chinh xac voi voice."""
    print("[5/7] Assembling video...")

    # Load voice per scene + get duration
    scene_voices = [AudioFileClip(str(p)) for p in scene_voice_paths]
    PAUSE = 0.2   # khoang lang ngan giua scene (Shorts cu phai nhanh)
    scene_durs = [v.duration + PAUSE for v in scene_voices]
    total_dur = sum(scene_durs)
    print(f"      Total duration: {total_dur:.1f}s ({len(scene_voices)} scenes)")

    # Build clips with matching per-scene durations
    target_w, target_h = 1080, 1920
    clips = []
    for i, (p, target_dur) in enumerate(zip(clip_paths, scene_durs)):
        c = VideoFileClip(str(p)).without_audio()
        scale = max(target_w / c.w, target_h / c.h)
        c = c.resize(scale)
        c = c.crop(x_center=c.w/2, y_center=c.h/2, width=target_w, height=target_h)
        if c.duration < target_dur:
            c = c.loop(duration=target_dur)
        else:
            c = c.subclip(0, target_dur)
        clips.append(c)

    video = concatenate_videoclips(clips, method="compose")

    # Build composite audio: voice scene 1 at t=0, scene 2 at t=dur1, ...
    from moviepy.editor import CompositeAudioClip
    audio_parts = []
    current_t = 0.0
    for v in scene_voices:
        audio_parts.append(v.set_start(current_t))
        current_t += v.duration + PAUSE  # gap silence

    # === BACKGROUND MUSIC ===
    bgm_files = list(BGM_DIR.glob("*.mp3")) if BGM_DIR.exists() else []
    if bgm_files:
        bgm_path = random.choice(bgm_files)
        print(f"      BGM: {bgm_path.name}")
        bgm = AudioFileClip(str(bgm_path)).volumex(0.12)  # 12% volume - du nho de khong at giong
        # Loop hoac trim BGM khop voi total duration
        if bgm.duration < total_dur:
            from moviepy.audio.fx.audio_loop import audio_loop
            bgm = audio_loop(bgm, duration=total_dur)
        else:
            bgm = bgm.subclip(0, total_dur)
        # Fade in/out 1s cho muot
        from moviepy.audio.fx.audio_fadein import audio_fadein
        from moviepy.audio.fx.audio_fadeout import audio_fadeout
        bgm = audio_fadein(bgm, 1.0)
        bgm = audio_fadeout(bgm, 1.5)
        audio_parts.append(bgm.set_start(0))
    else:
        print("      No BGM in audio/ folder (skip)")

    composite_audio = CompositeAudioClip(audio_parts)
    video = video.set_audio(composite_audio).set_duration(total_dur)

    # Font Vietnamese - cross-platform (macOS + Linux + Windows fallback)
    # Uu tien: Montserrat (TikTok aesthetic) -> Noto/DejaVu -> system default
    import os.path
    import glob as _glob
    _font_candidates = [
        # GitHub Actions (downloaded vao /tmp/fonts/)
        "/tmp/fonts/Montserrat-ExtraBold.ttf",
        "/tmp/fonts/Montserrat-Black.ttf",
        # macOS Homebrew fonts
        "/opt/homebrew/share/fonts/Montserrat-ExtraBold.ttf",
        "/opt/homebrew/share/fonts/NotoSans-Bold.ttf",
        # macOS system fonts (built-in, support Vietnamese tot)
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Avenir Next.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        # User-installed fonts macOS
        os.path.expanduser("~/Library/Fonts/Montserrat-ExtraBold.ttf"),
        os.path.expanduser("~/Library/Fonts/NotoSans-Bold.ttf"),
        # Linux (GitHub Actions Ubuntu)
        "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Windows (user-installed Montserrat / system fonts)
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/Montserrat-ExtraBold.ttf"),
        "C:/Windows/Fonts/Montserrat-ExtraBold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ]
    VN_FONT = next((p for p in _font_candidates if os.path.exists(p)), None)
    if not VN_FONT:
        # Fallback cuoi: tim BAT KY .ttf/.ttc nao trong system fonts cua Mac
        for pattern in [
            "/System/Library/Fonts/*.ttf",
            "/System/Library/Fonts/*.ttc",
            "/System/Library/Fonts/Supplemental/*.ttf",
            "/Library/Fonts/*.ttf",
        ]:
            matches = _glob.glob(pattern)
            if matches:
                VN_FONT = matches[0]
                break
    if not VN_FONT:
        # Cuoi cung: dung font name "Arial" va de MoviePy/IM tu tim
        VN_FONT = "Arial-Bold"
    print(f"      Font: {VN_FONT.split('/')[-1] if '/' in VN_FONT else VN_FONT}")

    # Disclaimer ALWAYS hien o top trong 4s dau
    disclaimer = (TextClip(DISCLAIMER_TEXT, fontsize=38, color="white",
                          bg_color="rgba(0,0,0,0.7)", size=(900, None),
                          method="caption", font=VN_FONT)
                  .set_position(("center", 100))
                  .set_start(0).set_duration(4))

    # === HOOK VISUAL — diem nhan 1.5s dau (TikTok/Shorts style) ===
    hook_text_raw = script_data["scenes"][0]["voiceover"]
    # Cat ngan: lay den dau ? . ! dau tien, hoac 7 tu dau
    import re as _re
    _m = _re.match(r"([^.?!]{1,80}[.?!])", hook_text_raw)
    if _m:
        hook_text = _m.group(1).strip()
    else:
        hook_text = " ".join(hook_text_raw.split()[:7]) + "..."
    # Gioi han do dai
    if len(hook_text) > 80:
        hook_text = hook_text[:77] + "..."
    print(f"      Hook: \"{hook_text}\"")

    hook_visual = (TextClip(hook_text, fontsize=110, color="yellow",
                           stroke_color="black", stroke_width=10,
                           size=(950, None), method="caption", font=VN_FONT)
                   .set_position(("center", 700))   # giua-tren man hinh
                   .set_start(0).set_duration(1.8)
                   .fadein(0.15).fadeout(0.3))

    # === KARAOKE-STYLE CAPTIONS ===
    # Chia voiceover moi scene thanh chunks 3-4 tu, hien sync voi voice
    def split_chunks(text, max_words=4):
        """Chia thanh cum 3-4 tu, uu tien ngat o dau cau."""
        # Tach theo dau phay/cham truoc
        import re as _re
        parts = _re.split(r'(?<=[,.;:!?])\s+', text.strip())
        chunks = []
        for part in parts:
            words = part.split()
            for i in range(0, len(words), max_words):
                chunk = " ".join(words[i:i + max_words])
                if chunk:
                    chunks.append(chunk)
        return chunks if chunks else [text]

    scene_captions = []
    start_t = 0.0
    for i, scene in enumerate(script_data["scenes"]):
        voice_dur = scene_voices[i].duration  # voice that su, khong tinh pause
        chunks = split_chunks(scene["voiceover"], max_words=4)
        if not chunks:
            start_t += scene_durs[i]
            continue
        # Chia deu thoi gian voice cho cac chunks
        chunk_dur = voice_dur / len(chunks)
        for j, chunk in enumerate(chunks):
            chunk_start = start_t + j * chunk_dur
            cap = (TextClip(chunk, fontsize=95, color="white",
                           stroke_color="black", stroke_width=8,
                           size=(950, None), method="caption", font=VN_FONT)
                   .set_position(("center", 1400))
                   .set_start(chunk_start).set_duration(chunk_dur))
            scene_captions.append(cap)
        start_t += scene_durs[i]

    final = CompositeVideoClip([video, hook_visual, disclaimer] + scene_captions)
    output = Path(tmpdir) / "final.mp4"

    # Memory optimization cho Windows (MoviePy 1.0.3 + nhieu TextClip):
    # - gc.collect() truoc khi render de free temp arrays
    # - threads=2 thay vi 4 (Windows MoviePy threading hay leak)
    # - dung file tam ro rang cho audio (tranh in-memory buffer)
    import gc as _gc
    _gc.collect()

    # Detect Windows de dieu chinh threads (Linux GitHub Actions van dung 4)
    import platform as _pl
    _threads = 2 if _pl.system() == "Windows" else 4

    try:
        final.write_videofile(
            str(output),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            bitrate="5500k",
            audio_bitrate="192k",
            threads=_threads,
            temp_audiofile=str(Path(tmpdir) / "temp_audio.m4a"),
            remove_temp=True,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            verbose=False,
            logger=None,
        )
    except (MemoryError, Exception) as e:
        # Fallback: neu MemoryError -> retry voi resolution 720x1280 (con 56% memory)
        if "MemoryError" in type(e).__name__ or "allocate" in str(e):
            print(f"      ⚠ Memory tight, retry voi 720x1280...")
            _gc.collect()
            final_lo = final.resize((720, 1280))
            final_lo.write_videofile(
                str(output),
                fps=30,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                bitrate="3500k",
                audio_bitrate="192k",
                threads=_threads,
                temp_audiofile=str(Path(tmpdir) / "temp_audio2.m4a"),
                remove_temp=True,
                ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                verbose=False,
                logger=None,
            )
        else:
            raise

    # Cleanup explicit cho Windows (force release file handles + memory)
    try:
        final.close()
        for _c in scene_captions:
            _c.close()
        hook_visual.close()
        disclaimer.close()
        video.close()
    except Exception:
        pass
    _gc.collect()

    print(f"      Saved: {output} ({output.stat().st_size // 1024} KB)")
    return output

# ==================== STEP 6: UPLOAD YOUTUBE ====================
def get_youtube_service():
    # Validate YT creds chi khi can upload (cho phep test_local.py bo qua)
    _require_env("YT_REFRESH_TOKEN", YT_REFRESH_TOKEN)
    _require_env("YT_CLIENT_ID", YT_CLIENT_ID)
    _require_env("YT_CLIENT_SECRET", YT_CLIENT_SECRET)
    creds = Credentials(
        token=None,
        refresh_token=YT_REFRESH_TOKEN,
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(video_path, script_data, idea):
    """Upload video lên YouTube với metadata đầy đủ + YMYL disclaimer."""
    print("[6/7] Uploading to YouTube...")
    yt = get_youtube_service()

    # Schedule publish ngày mai 06:00 sáng VN (= 23:00 UTC today)
    vn_tomorrow_6am = (datetime.now(timezone.utc) + timedelta(hours=24))
    vn_tomorrow_6am = vn_tomorrow_6am.replace(minute=0, second=0, microsecond=0)

    # Description với disclaimer YMYL
    full_desc = (
        f"{script_data['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ DISCLAIMER: Video chỉ mang tính giáo dục và chia sẻ góc nhìn cá nhân, "
        f"KHÔNG phải lời khuyên đầu tư hay tư vấn tài chính được cấp phép. "
        f"Mỗi người có hoàn cảnh tài chính khác nhau — hãy tham khảo chuyên gia "
        f"hoặc nhà tư vấn được cấp phép trước khi quyết định.\n\n"
        f"📚 Tham khảo: Uỷ ban Chứng khoán Nhà nước - ssc.gov.vn\n"
        f"📧 Liên hệ: taichinh5phut@gmail.com"
    )

    body = {
        "snippet": {
            "title": script_data["title"][:100],  # YouTube giới hạn 100
            "description": full_desc[:5000],
            "tags": script_data.get("tags", [])[:30],
            "categoryId": "27",  # Education
            "defaultLanguage": "vi",
            "defaultAudioLanguage": "vi",
        },
        "status": {
            "privacyStatus": "public",  # Hoặc "private" lúc đầu để check
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # YouTube 2026 BẮT BUỘC
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1,
                            resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"      Upload progress: {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"      ✅ Uploaded: https://youtube.com/watch?v={video_id}")
    return video_id

# ==================== MAIN ====================
def main():
    print("=" * 60)
    print(f"🚀 Pipeline started at {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. Pick idea
    idea, ideas = pick_next_idea()

    # 2. Load pre-generated script (Claude tao san, commit vao repo)
    script_data = load_script(idea)

    # 3-5. Make video in temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        clip_paths = fetch_all_clips(script_data["scenes"], tmpdir)
        scene_voice_paths = generate_voice_per_scene(script_data, tmpdir)
        video_path = assemble_video(clip_paths, scene_voice_paths, script_data, tmpdir)
        # 6. Upload
        video_id = upload_to_youtube(video_path, script_data, idea)

    # 7. Log
    mark_published(ideas, idea["id"], video_id)
    print("[7/7] Logged to published.json")
    print("=" * 60)
    print(f"Done! Video: https://youtube.com/watch?v={video_id}")
    print("=" * 60)

if __name__ == "__main__":
    main()
