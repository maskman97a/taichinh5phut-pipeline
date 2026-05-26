"""
Pipeline tự động tạo + upload 1 video YouTube Shorts mỗi ngày.
Kênh: Tài Chính 5 Phút

Flow: ideas.json -> Gemini script -> Pexels clips -> Edge TTS voice
   -> FFmpeg ghép video -> YouTube upload -> log published.json

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

from openai import OpenAI
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

# Fix MoviePy khong tu tim duoc ImageMagick (sau cache APT action)
import shutil as _shutil
from moviepy.config import change_settings as _change_settings
_imagemagick_path = (
    _shutil.which("convert")
    or _shutil.which("convert-im6.q16")
    or "/usr/bin/convert"
)
_change_settings({"IMAGEMAGICK_BINARY": _imagemagick_path})
print(f"[init] ImageMagick: {_imagemagick_path}")

# ==================== CONFIG ====================
GROQ_KEY = os.environ["GROQ_API_KEY"]
PEXELS_KEY = os.environ["PEXELS_API_KEY"]
YT_CLIENT_ID = os.environ["YT_CLIENT_ID"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]
GOOGLE_TTS_KEY = os.environ["GOOGLE_TTS_API_KEY"]

REPO_ROOT = Path(__file__).resolve().parent.parent
IDEAS_FILE = REPO_ROOT / "data" / "ideas.json"
PUBLISHED_FILE = REPO_ROOT / "data" / "published.json"
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

# ==================== STEP 2: SINH SCRIPT (GEMINI) ====================
def generate_script(idea):
    """Goi Groq (Llama 3.3 70B) sinh script HSCV + 8 scene voi visual_keyword."""
    client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")

    prompt = f"""Bạn là editor TOP 1% của kênh YouTube tài chính Việt Nam "Tài Chính 5 Phút".

NHIỆM VỤ: Tạo 1 video YouTube Shorts 45-55 giây về chủ đề: "{idea['title']}"
Pillar: {idea.get('pillar', 'general')}

⚠️ QUY TẮC NGÔN NGỮ TUYỆT ĐỐI (BẮT BUỘC):
- TẤT CẢ output bao gồm title, description, voiceover, tags PHẢI viết bằng TIẾNG VIỆT CÓ DẤU ĐẦY ĐỦ
- Dùng ký tự: à á ả ã ạ ă ắ ằ ẳ ẵ ặ â ấ ầ ẩ ẫ ậ đ è é ẻ ẽ ẹ ê ế ề ể ễ ệ ì í ỉ ĩ ị ò ó ỏ õ ọ ô ố ồ ổ ỗ ộ ơ ớ ờ ở ỡ ợ ù ú ủ ũ ụ ư ứ ừ ử ữ ự ỳ ý ỷ ỹ ỵ
- TUYỆT ĐỐI KHÔNG viết tiếng Việt không dấu kiểu "Tai Chinh" thay vì "Tài Chính"
- CHỈ visual_keyword là TIẾNG ANH (cho Pexels search)

LUẬT NỘI DUNG TUYỆT ĐỐI:

[1] HOOK SCENE 1 (3 giây, 8-12 từ):
   - 1 câu hỏi SHOCK hoặc tuyên bố gây tò mò
   - PHẢI có con số cụ thể (vd: "90%", "10 triệu", "5 phút")
   - Ví dụ TỐT: "90% người Việt lương 15 triệu vẫn hết tiền cuối tháng. Vì sao?"
   - Ví dụ TỆ: "Hôm nay chúng ta nói về quản lý tiền." (NHẠT — BỎ!)

[2] SETUP SCENE 2 (5-7 giây):
   - Mô tả NỖI ĐAU cụ thể của dân văn phòng Việt
   - Tình huống quen thuộc: cuối tháng nhẵn ví, đầu tháng tiêu hết lương, sợ đầu tư vì mất tiền

[3] CỐT LÕI SCENE 3-6 (30-35 giây):
   - Trình bày GIẢI PHÁP cụ thể, KHÔNG lý thuyết suông
   - ĐẦY ĐỦ CON SỐ: vd "Lương 15 triệu → 7.5 triệu sinh hoạt + 4.5 triệu hưởng thụ + 3 triệu đầu tư"
   - Mỗi scene 1 ý chính rõ ràng
   - SCENE 5 hoặc 6: BẮT BUỘC chèn câu "Tôi áp dụng cách này X tháng và thấy [kết quả cụ thể]"
   - Tránh từ ngữ academic. Nói như bạn bè 28 tuổi nói với nhau

[4] CTA SCENE 7-8 (5-10 giây):
   - Scene 7: 1 câu tóm tắt hoặc câu hỏi mở để comment
   - Scene 8: "Theo dõi để học mỗi ngày 1 mẹo tiền. Đây là góc nhìn cá nhân, không phải lời khuyên tài chính."

VOICEOVER:
   - Mỗi scene: 1-2 câu ngắn
   - DÙNG dấu chấm/phẩy đúng cách để TTS đọc có ngắt nghỉ tự nhiên
   - KHÔNG viết "[disclaimer]" trong text — viết tự nhiên

VISUAL_KEYWORD (cho Pexels search, TIẾNG ANH):
   - 2-4 từ tiếng Anh cụ thể (KHÔNG generic)
   - Tốt: "hand counting cash vietnamese", "young office worker stressed", "stock chart green rising"
   - Tệ: "money", "business", "finance" (quá chung chung)
   - Mỗi scene khác nhau hoàn toàn: mix wide shot + close-up + abstract

YMYL COMPLIANCE (BẮT BUỘC):
   - Scene 8 PHẢI có câu disclaimer
   - KHÔNG khuyến nghị mua cổ phiếu cụ thể
   - KHÔNG hứa hẹn ROI

TRẢ VỀ JSON (chỉ JSON, không markdown wrapping):
{{
  "title": "<60 ký tự, TIẾNG VIỆT CÓ DẤU, có #shorts cuối, gây tò mò",
  "description": "200-300 từ TIẾNG VIỆT CÓ DẤU gồm: hook 2 câu + disclaimer ngắn + 3 link affiliate placeholder [LINK_VPS] [LINK_INFINA] [LINK_TPBANK] + CTA subscribe + 5 hashtag",
  "tags": ["thẻ tiếng việt có dấu", "tag tiếng anh ok", ...],
  "scenes": [
    {{"voiceover": "TIẾNG VIỆT CÓ DẤU đầy đủ", "visual_keyword": "english only"}},
    ... 8 scenes
  ]
}}

NHẮC LẠI: KIỂM TRA OUTPUT, BẢO ĐẢM CÓ ĐẦY ĐỦ DẤU TIẾNG VIỆT. Chủ đề: "{idea['title']}"."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        response_format={"type": "json_object"},
        max_tokens=4096,
    )
    text = response.choices[0].message.content.strip()
    # Clean neu wrap trong ```json
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)

    print(f"[2/7] Generated script: {data['title']}")
    print(f"      Scenes: {len(data['scenes'])}")
    return data

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
                "speakingRate": 1.0,
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
    PAUSE = 0.35  # khoang lang 0.35s giua moi scene (cho tu nhien)
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

    # Font Vietnamese (DejaVu/Noto support full Unicode)
    # Font Vietnamese - Montserrat (viral TikTok aesthetic) -> fallback Noto -> DejaVu
    import os.path
    _font_candidates = [
        "/tmp/fonts/Montserrat-ExtraBold.ttf",
        "/tmp/fonts/Montserrat-Black.ttf",
        "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    VN_FONT = next((p for p in _font_candidates if os.path.exists(p)), _font_candidates[-1])
    print(f"      Font: {VN_FONT.split('/')[-1]}")

    # Disclaimer ALWAYS hien o top trong 4s dau
    disclaimer = (TextClip(DISCLAIMER_TEXT, fontsize=38, color="white",
                          bg_color="rgba(0,0,0,0.7)", size=(900, None),
                          method="caption", font=VN_FONT)
                  .set_position(("center", 100))
                  .set_start(0).set_duration(4))

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

    final = CompositeVideoClip([video, disclaimer] + scene_captions)
    output = Path(tmpdir) / "final.mp4"
    final.write_videofile(
        str(output),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",     # Balance giua speed va quality
        bitrate="5500k",     # Hoi giam tu 6000k de fit "medium" preset
        audio_bitrate="192k",
        threads=4,           # GitHub Actions co 4 cores
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        verbose=False,
        logger=None,
    )
    print(f"      Saved: {output} ({output.stat().st_size // 1024} KB)")
    return output

# ==================== STEP 6: UPLOAD YOUTUBE ====================
def get_youtube_service():
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

    # 2. Generate script
    script_data = generate_script(idea)

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
