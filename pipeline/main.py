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

# Xoay vòng 4 voice Google WaveNet cho de-templating
VOICES = [
    "vi-VN-Wavenet-A",  # Female 1
    "vi-VN-Wavenet-B",  # Male 1
    "vi-VN-Wavenet-C",  # Female 2
    "vi-VN-Wavenet-D",  # Male 2
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

    prompt = f"""Ban la editor TOP 1% cua kenh YouTube tai chinh Viet Nam "Tai Chinh 5 Phut".

NHIEM VU: Tao 1 video YouTube Shorts 45-55 giay ve: "{idea['title']}"
Pillar: {idea.get('pillar', 'general')}

LUAT TUYET DOI (lam sai = video FLOP):

[1] HOOK SCENE 1 (3 giay, 8-12 tu):
   - 1 cau hoi SHOCK hoac cau tuyen bo gay to mo
   - PHAI co con so cu the (vd: "90%", "10 trieu", "5 phut")
   - Vi du tot: "90% nguoi Viet luong 15tr van het tien cuoi thang. Vi sao?"
   - Vi du te: "Hom nay chung ta noi ve quan ly tien." (NHAT, BO!)

[2] SETUP SCENE 2 (5-7 giay):
   - Mo ta NOI DAU cu the cua dan VP Viet
   - Tinh huong quen thuoc: cuoi thang nhan vi, dau thang tieu het luong, so dau tu vi mat tien

[3] COT LOI SCENE 3-6 (30-35 giay):
   - Trinh bay GIAI PHAP cu the, KHONG ly thuyet
   - DAY DU CON SO: vd "Luong 15tr -> 7.5tr sinh hoat + 4.5tr huong thu + 3tr dau tu"
   - Moi scene 1 y chinh ro rang
   - SCENE 5 hoac 6: BAT BUOC chen cau "Toi ap dung cach nay X thang va thay [ket qua cu the]"
   - Tranh tu ngu academic. Noi nhu ban be 28 tuoi noi voi nhau

[4] CTA SCENE 7-8 (5-10 giay):
   - Scene 7: 1 cau tom tat hoac 1 cau hoi mo de comment
   - Scene 8: "Theo doi de hoc moi ngay 1 meo tien. Day la goc nhin ca nhan, khong phai loi khuyen tai chinh."

VOICEOVER:
   - Moi scene: 1-2 cau ngan
   - DUNG cham/phay dung cach de TTS doc co ngat nghi tu nhien
   - KHONG viet "[disclaimer]" trong text - viet tu nhien

VISUAL_KEYWORD (cho Pexels search):
   - 2-4 tu TIENG ANH cu the (KHONG generic)
   - Tot: "hand counting cash vietnamese", "young office worker stressed", "stock chart green rising"
   - Te: "money", "business", "finance" (qua chung chung)
   - Moi scene khac nhau hoan toan: mix wide shot + close-up + abstract

YMYL COMPLIANCE (BAT BUOC):
   - Scene 8 PHAI co cau disclaimer
   - KHONG khuyen nghi mua co phieu cu the
   - KHONG hua hen ROI

TRA VE JSON (chi JSON, khong markdown wrapping):
{{
  "title": "<60 ky tu, co #shorts cuoi, gay to mo",
  "description": "200-300 tu gom: hook 2 cau + disclaimer ngan + 3 link affiliate placeholder [LINK_VPS] [LINK_INFINA] [LINK_TPBANK] + CTA subscribe + 5 hashtag",
  "tags": ["tag1", "tag2", ...],
  "scenes": [
    {{"voiceover": "...", "visual_keyword": "..."}},
    {{"voiceover": "...", "visual_keyword": "..."}},
    ... 8 scenes
  ]
}}

Tra ve 8 scenes. Chu de: "{idea['title']}"."""

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
    """Tải toàn bộ clip cho 8 scene."""
    paths = []
    for i, scene in enumerate(scenes):
        path = Path(tmpdir) / f"clip_{i}.mp4"
        kw = scene["visual_keyword"]
        print(f"[3/7] Downloading clip {i+1}/8: '{kw}'")
        try:
            download_pexels_clip(kw, path)
            paths.append(path)
        except Exception as e:
            print(f"      ⚠️ Failed '{kw}': {e}. Retrying with 'business'...")
            download_pexels_clip("business meeting", path)
            paths.append(path)
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
    VN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # Disclaimer ALWAYS hien o top trong 4s dau
    disclaimer = (TextClip(DISCLAIMER_TEXT, fontsize=40, color="white",
                          bg_color="black", size=(900, None),
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
            cap = (TextClip(chunk, fontsize=85, color="yellow",
                           stroke_color="black", stroke_width=6,
                           size=(900, None), method="caption", font=VN_FONT)
                   .set_position(("center", 1450))
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
        preset="slow",       # Quality cao hon (cham encode hon)
        bitrate="6000k",     # Tang tu 3000 -> 6000k
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
