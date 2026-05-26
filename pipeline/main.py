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

import edge_tts
import google.generativeai as genai
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy.editor import (AudioFileClip, CompositeAudioClip,
                            CompositeVideoClip, TextClip, VideoFileClip,
                            concatenate_videoclips)

# ==================== CONFIG ====================
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_KEY = os.environ["PEXELS_API_KEY"]
YT_CLIENT_ID = os.environ["YT_CLIENT_ID"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]

REPO_ROOT = Path(__file__).resolve().parent.parent
IDEAS_FILE = REPO_ROOT / "data" / "ideas.json"
PUBLISHED_FILE = REPO_ROOT / "data" / "published.json"

# Xoay vòng voice mỗi ngày cho de-templating
VOICES = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]

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
    """Gọi Gemini sinh script HSCV + 8 scene với visual_keyword."""
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""Bạn là editor kênh YouTube tài chính "Tài Chính 5 Phút" tiếng Việt.

Tạo 1 video Short 45-55 giây về chủ đề: "{idea['title']}"
Pillar: {idea.get('pillar', 'general')}

YÊU CẦU YMYL (BẮT BUỘC):
- Scene 1 hiển thị text disclaimer: "Video giáo dục, không phải lời khuyên đầu tư"
- Scene cuối voice-over có câu "Đây là góc nhìn cá nhân, không phải lời khuyên tài chính"
- KHÔNG khuyến nghị mua cổ phiếu cụ thể, KHÔNG hứa hẹn ROI

CẤU TRÚC: HSCV (Hook 3s - Setup 7s - Cốt lõi 30-35s - Value+CTA 5-10s)
- Hook ≤ 10 từ, gây tò mò/shock
- Chèn 1 câu "góc nhìn cá nhân" trong Cốt lõi
- Văn phong tiếng Việt nói tự nhiên

CHIA THÀNH 8 SCENE đều nhau. Mỗi scene có:
- voiceover: text tiếng Việt sẽ đọc (1-2 câu)
- visual_keyword: 2-4 từ TIẾNG ANH để search Pexels (đa dạng, mỗi scene khác nhau)

TRẢ VỀ JSON THUẦN (KHÔNG có ```json wrapping):
{{
  "title": "tiêu đề cuối <60 ký tự, có #shorts",
  "description": "200-300 từ, gồm: hook 2 câu + disclaimer ngắn + 3 link affiliate [LINK_VPS] [LINK_INFINA] [LINK_TPBANK] + CTA subscribe",
  "tags": ["tag1", "tag2", ...],  // 15-20 tag tiếng Việt + Anh
  "scenes": [
    {{"voiceover": "...", "visual_keyword": "..."}},
    ...8 scenes...
  ]
}}"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    # Clean nếu Gemini wrap trong ```json
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
            "size": "medium",
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
    target = next((f for f in video_files if f.get("width", 0) >= 720), video_files[-1])

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

# ==================== STEP 4: SINH VOICE (EDGE TTS) ====================
async def generate_voice_async(text, output_path, voice):
    communicate = edge_tts.Communicate(text, voice, rate="+5%")
    await communicate.save(str(output_path))

def generate_voice(script_data, tmpdir):
    """Sinh voice cho toàn bộ video. Xoay vòng voice mỗi ngày."""
    # Xoay vòng voice theo ngày
    voice = VOICES[datetime.now().day % len(VOICES)]
    full_text = " ".join(s["voiceover"] for s in script_data["scenes"])
    path = Path(tmpdir) / "voice.mp3"
    print(f"[4/7] Generating voice ({voice})...")
    asyncio.run(generate_voice_async(full_text, path, voice))
    return path

# ==================== STEP 5: GHÉP VIDEO (MOVIEPY) ====================
def assemble_video(clip_paths, voice_path, script_data, tmpdir):
    """Ghép 8 clip + voice + caption + disclaimer scene 1."""
    print("[5/7] Assembling video...")
    voice = AudioFileClip(str(voice_path))
    total_dur = voice.duration
    scene_dur = total_dur / len(clip_paths)

    # Crop/resize each clip vertical 1080x1920, trim to scene_dur
    clips = []
    for i, p in enumerate(clip_paths):
        c = VideoFileClip(str(p)).without_audio()
        # Resize to 1080x1920 (vertical 9:16)
        target_w, target_h = 1080, 1920
        # Scale to cover (have to crop to maintain aspect)
        scale = max(target_w / c.w, target_h / c.h)
        c = c.resize(scale)
        c = c.crop(x_center=c.w/2, y_center=c.h/2, width=target_w, height=target_h)
        # Trim to scene_dur (loop if too short)
        if c.duration < scene_dur:
            c = c.loop(duration=scene_dur)
        else:
            c = c.subclip(0, scene_dur)
        clips.append(c)

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(voice).set_duration(total_dur)

    # Caption overlay — disclaimer at scene 1 (first 3 seconds)
    disclaimer = (TextClip(DISCLAIMER_TEXT, fontsize=42, color="white",
                          bg_color="black", size=(900, None),
                          method="caption")
                  .set_position(("center", 100))
                  .set_start(0).set_duration(3))

    # Word-by-word captions (simplified — by scene)
    scene_captions = []
    for i, scene in enumerate(script_data["scenes"]):
        start = i * scene_dur
        # Wrap text every ~30 chars
        cap_text = scene["voiceover"]
        if len(cap_text) > 80:
            cap_text = cap_text[:77] + "..."
        cap = (TextClip(cap_text, fontsize=56, color="yellow",
                       stroke_color="black", stroke_width=3,
                       size=(960, None), method="caption")
               .set_position(("center", 1500))
               .set_start(start).set_duration(scene_dur))
        scene_captions.append(cap)

    final = CompositeVideoClip([video, disclaimer] + scene_captions)
    output = Path(tmpdir) / "final.mp4"
    final.write_videofile(
        str(output),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="3000k",
        threads=2,
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
        voice_path = generate_voice(script_data, tmpdir)
        video_path = assemble_video(clip_paths, voice_path, script_data, tmpdir)
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
