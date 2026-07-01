"""
Pipeline tự động tạo + upload 1 video YouTube Shorts mỗi ngày.
Niche: Tự động hóa & mẹo dùng AI trong đời sống (VN) — daily AI tips/automation Shorts.

Flow: ideas.json -> LOAD pre-generated script (data/scripts/{id}.json)
   -> AI image (Pollinations Flux) / Pexels clips -> Google TTS vi-VN voice
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
# iter 20 RULE "khong lap content": luu Pexels video_id da dung XUYEN SUOT moi video
# -> moi video lay footage khac nhau, khong bao gio trung clip.
USED_PEXELS_FILE = REPO_ROOT / "data" / "used_pexels.json"


def load_used_pexels():
    """Doc set Pexels video_id da dung o cac video truoc (cross-video dedup)."""
    if USED_PEXELS_FILE.exists():
        try:
            with open(USED_PEXELS_FILE, "r", encoding="utf-8-sig") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_used_pexels(ids):
    """Ghi lai set Pexels video_id da dung (giu toi da 500 ID gan nhat de tranh file phinh)."""
    try:
        id_list = list(ids)[-500:]
        with open(USED_PEXELS_FILE, "w", encoding="utf-8") as f:
            json.dump(id_list, f)
    except Exception as e:
        print(f"      ⚠ Khong luu duoc used_pexels.json: {e}")
IMAGES_DIR = REPO_ROOT / "data" / "images"  # Anh curated (visual_style="local") - niche AI dung visual_style="ai"
BGM_DIR = REPO_ROOT / "audio"  # Folder chua background music (.mp3) - tech/electronic hop niche AI

# Rotate Vietnamese voices (niche AI/tu dong hoa - VN, iter 20 pivot)
# Mix nam + nu de de-templating + giong than thien huong dan (khong phai ke chuyen the thao).
# Neural2 vi-VN tu nhien hon Wavenet, co inflection.
# iter 20: KHOA 1 GIONG cho nhat quan thuong hieu (bo xoay nam/nu - user thay "sai giong").
# Da dang tu noi dung, khong phai tu doi giong. Override qua env VOICE_NAME neu can.
VOICES = [
    os.environ.get("VOICE_NAME", "vi-VN-Neural2-D"),   # Nam tram, manh me, tu nhien (Neural2)
]

# Disclaimer cho niche AI/cong nghe (ngan gon - iter 20: tranh che 1/4 man hinh luc hook)
DISCLAIMER_TEXT = "Hình ảnh minh họa tạo bằng AI."

# ==================== STEP 1: LẤY Ý TƯỞNG ====================
def pick_next_idea():
    """Lấy idea đầu tiên có status='todo' từ ideas.json."""
    with open(IDEAS_FILE, "r", encoding="utf-8-sig") as f:
        ideas = json.load(f)
    todo = [i for i in ideas if i.get("status") == "todo"]
    if not todo:
        print("Het y tuong! Vui long them moi vao ideas.json")
        sys.exit(0)
    picked = todo[0]
    print(f"[1/7] Picked idea #{picked['id']}: {picked['title']}")
    return picked, ideas

def mark_published(ideas, idea_id, video_id, bgm_file=None):
    """Mark idea đã đăng, append vào published.json (kèm log BGM file để trace copyright claim)."""
    for i in ideas:
        if i["id"] == idea_id:
            i["status"] = "published"
            i["video_id"] = video_id
            i["published_at"] = datetime.now(timezone.utc).isoformat()
    with open(IDEAS_FILE, "w", encoding="utf-8") as f:
        json.dump(ideas, f, ensure_ascii=False, indent=2)
    # Append published log (kèm bgm_file để trace nếu bị YouTube Content ID claim)
    log = []
    if PUBLISHED_FILE.exists():
        with open(PUBLISHED_FILE, "r", encoding="utf-8-sig") as f:  # utf-8-sig: chiu duoc BOM
            log = json.load(f)
    entry = {
        "idea_id": idea_id,
        "video_id": video_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    if bgm_file:
        entry["bgm_file"] = bgm_file
    log.append(entry)
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

    with open(script_path, encoding="utf-8-sig") as f:
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
def generate_ai_image(prompt, output_path, width=1080, height=1920, seed=None):
    """Generate AI image via Pollinations (free, no API key).

    iter 17: Retry logic + model fallback (flux -> turbo).
    Pollinations 402 Payment Required intermittent rate limit -> try turbo + delay.

    Returns image bytes via URL params.
    """
    import urllib.parse, time
    if seed is None:
        seed = random.randint(1, 999999)
    # iter 20: style anchor de dong nhat aesthetic + tranh anime/cartoon (Flux hay drift)
    STYLE_ANCHOR = (", professional 3d render, sleek modern tech aesthetic, "
                    "cinematic studio lighting, high detail, sharp focus, clean composition, "
                    "no text, no watermark, not anime, not cartoon character, photorealistic")
    full_prompt = (prompt + STYLE_ANCHOR)[:600]
    encoded = urllib.parse.quote(full_prompt)

    # Try sequence: flux -> turbo (2 attempts each with backoff)
    attempts = [
        ("flux", 0),
        ("turbo", 5),
        ("flux", 15),
        ("turbo", 20),
    ]
    last_err = None
    for model, delay in attempts:
        if delay:
            time.sleep(delay)
        # enhance=true: Pollinations tu nang prompt -> chi tiet/dep hon. nofeed=true: khong public feed.
        url = (f"https://image.pollinations.ai/prompt/{encoded}"
               f"?width={width}&height={height}&seed={seed}&model={model}"
               f"&nologo=true&enhance=true&nofeed=true")
        try:
            resp = requests.get(url, timeout=90, stream=True)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Verify file size > 5KB (otherwise placeholder)
                if Path(output_path).stat().st_size > 5 * 1024:
                    return output_path
                last_err = f"{model}: file too small"
            else:
                last_err = f"{model}: HTTP {resp.status_code}"
        except Exception as e:
            last_err = f"{model}: {e}"
    raise RuntimeError(f"Pollinations all retries failed: {last_err}")


def image_to_video_kenburns(image_path, video_path, duration=10.0, target_w=1080, target_h=1920):
    """Convert image to vertical video with smooth Ken Burns effect via FFmpeg.

    SMOOTH linear zoom 1.0 -> 1.15 across duration (khong giat khung hinh).
    Duration default 10s -> cover max scene duration, assembly subclip to exact.
    """
    import subprocess
    fps = 24
    total_frames = int(duration * fps)
    # SMOOTH linear zoom: z = 1.0 + (max_zoom - 1.0) * (on/total_frames)
    # Use 'on' (current output frame number) for linear interpolation
    max_zoom = 1.15
    zoompan = (f"zoompan=z='1.0+({max_zoom}-1.0)*on/{total_frames}':"
               f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
               f"d={total_frames}:s={target_w}x{target_h}:fps={fps}")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(image_path),
        # iter 20: COVER-fit (giu ty le, scale phu kin khung roi crop giua) - tranh anh
        # khong-9:16 bi keo dep/dai ngoang. Truoc day scale=-1:H*2 lam vat tron thanh ellipse.
        "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase:flags=lanczos,crop={target_w}:{target_h},{zoompan}",
        "-t", f"{duration:.2f}",
        "-r", str(fps),  # explicit output fps
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        str(video_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video_path


def image_to_video_fit_blur(image_path, video_path, duration=15.0, target_w=1080, target_h=1920):
    """Convert image to vertical video — FIT toan bo anh + nen MO (iter 19).

    Cho anh nguoi/landscape ty le khong dong dang (vd anh bao chi):
    - Background: anh scale COVER (fill) + blur manh -> lap day khung
    - Foreground: anh scale CONTAIN (fit toan bo, KHONG crop) o giua
    - Ken Burns zoom nhe 1.0->1.08 tren ca composite

    Tranh loi crop sat mat khi anh landscape ep vao khung doc.
    """
    import subprocess
    fps = 24
    total_frames = int(duration * fps)
    # Background: cover + crop full frame + gaussian blur manh
    # Foreground: contain (fit), giu nguyen ty le, khong crop
    # Overlay fg giua bg -> zoompan nhe tren ket qua
    filter_complex = (
        f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},gblur=sigma=28[bg];"
        f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[ov];"
        f"[ov]zoompan=z='1.0+0.08*on/{total_frames}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={target_w}x{target_h}:fps={fps}"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(image_path),
        "-filter_complex", filter_complex,
        "-t", f"{duration:.2f}",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        str(video_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video_path


def download_pexels_clip(keyword, output_path, exclude_ids=None):
    """Tải 1 video vertical từ Pexels theo keyword.

    exclude_ids: set chứa Pexels video_id đã dùng -> SKIP để tránh duplicate.
    per_page 15 (was 5) -> nhieu lua chon hon, ti le trung thap.
    Returns: video_id đã chọn (de caller add vao exclude_ids).
    """
    if exclude_ids is None:
        exclude_ids = set()
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_KEY},
        params={
            "query": keyword,
            "orientation": "portrait",
            "size": "large",
            "per_page": 15,  # was 5 - cho nhieu lua chon hon
        },
        timeout=30,
    )
    r.raise_for_status()
    videos = r.json().get("videos", [])

    # Loc bo video da dung
    available = [v for v in videos if v["id"] not in exclude_ids]

    if not available:
        # Tat ca da dung -> thu fallback search broader
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": "business", "orientation": "portrait", "per_page": 20},
            timeout=30,
        )
        videos = r.json().get("videos", [])
        available = [v for v in videos if v["id"] not in exclude_ids]
        if not available:
            # Het cach -> pick bat ky (chap nhan duplicate hiem hoi)
            available = videos if videos else []

    if not available:
        raise RuntimeError(f"Pexels khong tra ket qua nao cho '{keyword}'")

    chosen = random.choice(available)
    # Tìm file HD vertical
    video_files = sorted(chosen["video_files"],
                         key=lambda f: f.get("width", 0))
    target = next((f for f in video_files if f.get("width", 0) >= 1080), video_files[-1])

    resp = requests.get(target["link"], stream=True, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return chosen["id"]


def fetch_all_clips(scenes, tmpdir, idea_id=None):
    """Tai toan bo clip SEQUENTIAL.

    Strategy per scene:
    0. visual_style="local" -> doc anh curated tu data/images/{idea_id}/ + Ken Burns
    1. Try Pexels stock (with dedup via exclude_ids)
    2. Fallback: AI image gen (Pollinations Flux) + Ken Burns to video
    3. Last resort: Pexels broad search

    Script JSON co the chi dinh 'visual_style': 'local'|'stock'|'ai'|'auto' (default auto).
    visual_file: ten file anh trong data/images/{idea_id}/ (cho style="local").
    """
    print(f"[3/7] Fetching {len(scenes)} clips...")
    used_ids = load_used_pexels()  # RULE khong lap: loai tru footage da dung o video truoc
    if used_ids:
        print(f"      (cross-video dedup: tranh {len(used_ids)} Pexels clip da dung)")
    paths = [None] * len(scenes)
    img_folder = (IMAGES_DIR / str(idea_id)) if idea_id is not None else None

    for i, scene in enumerate(scenes):
        path = Path(tmpdir) / f"clip_{i}.mp4"
        kw = scene.get("visual_keyword", "")
        style = scene.get("visual_style", "auto").lower()
        ai_prompt = scene.get("visual_prompt") or kw  # explicit AI prompt or reuse keyword

        # visual_style="local" -> anh curated tu data/images/{idea_id}/
        if style == "local":
            try:
                # Tim file: visual_file chi dinh, hoac mac dinh {i}.jpg/png
                vf = scene.get("visual_file", "")
                local_img = None
                if vf and img_folder and (img_folder / vf).exists():
                    local_img = img_folder / vf
                elif img_folder:
                    # Fallback: tim {i}.jpg/png/jpeg/webp
                    for ext in (".jpg", ".jpeg", ".png", ".webp"):
                        cand = img_folder / f"{i}{ext}"
                        if cand.exists():
                            local_img = cand
                            break
                if not local_img:
                    raise FileNotFoundError(
                        f"Khong tim thay anh local cho scene {i} trong {img_folder} "
                        f"(visual_file='{vf}')")
                # FIT + blur background 15s (anh nguoi/bao chi ty le bat ky -> khong crop sat mat)
                image_to_video_fit_blur(str(local_img), path, duration=15.0)
                paths[i] = path
                print(f"      Clip {i+1}/{len(scenes)}: local '{local_img.name}' -> fit+blur OK")
                continue
            except Exception as e:
                print(f"      Clip {i+1}/{len(scenes)}: local fail ({e}), fallback AI")
                style = "ai"  # fallback to AI gen

        # Force AI mode (skip Pexels)
        if style == "ai":
            try:
                img_path = Path(tmpdir) / f"img_{i}.jpg"
                # iter 20: gen VUONG 1024x1024 -> model ve vat the dung dang (cau tron ra tron),
                # KHONG bi keo dai nhu khi gen 9:16. Bo "vertical/portrait" khoi prompt.
                sq_prompt = re.sub(r',?\s*(vertical|portrait)\b', '', ai_prompt, flags=re.I).strip().rstrip(",")
                sq_prompt += ", centered composition, full subject visible in frame"
                generate_ai_image(sq_prompt, img_path, width=1024, height=1024)
                # FIT + nen mo (contain): giu nguyen ty le vat the, khong crop/meo
                image_to_video_fit_blur(img_path, path, duration=15.0)
                paths[i] = path
                print(f"      Clip {i+1}/{len(scenes)}: '{kw}' -> AI image (square+fit) OK")
                continue
            except Exception as e:
                print(f"      Clip {i+1}/{len(scenes)}: AI fail ({e}), fallback Pexels")
                style = "auto"  # fallback to Pexels

        # Try Pexels first
        if style != "ai":
            try:
                vid = download_pexels_clip(kw, path, exclude_ids=used_ids)
                used_ids.add(vid)
                paths[i] = path
                print(f"      Clip {i+1}/{len(scenes)}: '{kw}' -> Pexels OK (id={vid})")
                continue
            except Exception as pex_e:
                # Pexels failed - fallback to AI image if 'auto' style
                if style == "auto":
                    try:
                        img_path = Path(tmpdir) / f"img_{i}.jpg"
                        sq_prompt = re.sub(r',?\s*(vertical|portrait)\b', '', ai_prompt, flags=re.I).strip().rstrip(",")
                        sq_prompt += ", centered composition, full subject visible in frame"
                        generate_ai_image(sq_prompt, img_path, width=1024, height=1024)
                        image_to_video_fit_blur(img_path, path, duration=15.0)
                        paths[i] = path
                        print(f"      Clip {i+1}/{len(scenes)}: Pexels fail -> AI image (square+fit) OK")
                        continue
                    except Exception as ai_e:
                        print(f"      Clip {i+1}/{len(scenes)}: AI also fail ({ai_e})")

                # Last resort: Pexels broad search
                try:
                    vid = download_pexels_clip("business meeting", path, exclude_ids=used_ids)
                    used_ids.add(vid)
                    paths[i] = path
                    print(f"      Clip {i+1}/{len(scenes)}: broad fallback OK")
                except Exception as e2:
                    print(f"      Clip {i+1}/{len(scenes)}: ALL FAIL ({e2})")
                    paths[i] = None

    save_used_pexels(used_ids)  # persist de video sau khong lay lai cung footage
    return paths

# ==================== STEP 4: SINH VOICE (GOOGLE CLOUD TTS WAVENET) ====================
import base64
import html as _html

def split_chunks_text(text, max_words=3):
    """Module-level chunk splitter (shared TTS SSML + assembly caption).

    Chia thanh cum 3 tu, uu tien ngat o dau cau (,.;:!?).
    """
    parts = re.split(r'(?<=[,.;:!?])\s+', text.strip())
    chunks = []
    for part in parts:
        words = part.split()
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i:i + max_words])
            if chunk:
                chunks.append(chunk)
    return chunks if chunks else [text]


# ==================== CAPTION DISPLAY TRANSFORM (iter 20) ====================
# Chi ap dung cho TEXT HIEN THI tren caption/hook (KHONG dung cho TTS -> giong khong doi):
#   1. So bang chu -> so (ba muoi giay -> 30 giay, muoi -> 10), giu nguyen don vi.
#   2. Bo dau cau . , : ; va gach ngang — –  (giu ? !).
_DIGIT = {'không': 0, 'một': 1, 'hai': 2, 'ba': 3, 'bốn': 4, 'năm': 5, 'sáu': 6,
          'bảy': 7, 'tám': 8, 'chín': 9, 'mốt': 1, 'lăm': 5, 'tư': 4, 'bẩy': 7}
_NUMWORDS = set(_DIGIT) | {'mười', 'mươi', 'trăm'}


def _vn_digit(w):
    return _DIGIT.get(w, 0)


def _vn_tens(toks):
    """Parse 0-99 tu list token (khong co 'trăm')."""
    if not toks:
        return 0
    if toks[0] == 'mười':
        return 10 + (_vn_digit(toks[1]) if len(toks) > 1 else 0)
    if len(toks) >= 2 and toks[1] == 'mươi':
        return _vn_digit(toks[0]) * 10 + (_vn_digit(toks[2]) if len(toks) > 2 else 0)
    return _vn_digit(toks[0])


def _vn_value(toks):
    if 'trăm' in toks:
        k = toks.index('trăm')
        hundreds = _vn_digit(toks[k - 1]) if k > 0 else 1
        rest = toks[k + 1:]
        if rest and rest[0] in ('lẻ', 'linh'):
            rest = rest[1:]
        return hundreds * 100 + _vn_tens(rest)
    return _vn_tens(toks)


def _vn_run_to_digits(toks):
    """Doi 1 run so -> chuoi so. Xu ly 'X năm' (nam = nam thang) khi 2 digit tran khong scale."""
    has_scale = any(t in ('mười', 'mươi', 'trăm') for t in toks)
    if not has_scale and len(toks) == 2 and toks[1] == 'năm' and toks[0] in _DIGIT:
        return f"{_vn_digit(toks[0])} năm"
    return str(_vn_value(toks))


def vn_numbers_to_digits(text):
    """Doi cac cum so bang chu trong text -> chu so (display only)."""
    toks = text.split()
    out, i = [], 0
    while i < len(toks):
        core = re.sub(r'[^\wÀ-ỹ]', '', toks[i]).lower()
        if core in _NUMWORDS:
            run, j = [], i
            while j < len(toks):
                c = re.sub(r'[^\wÀ-ỹ]', '', toks[j]).lower()
                if c in _NUMWORDS:
                    run.append(c)
                    j += 1
                else:
                    break
            tail = re.sub(r'^[\wÀ-ỹ]+', '', toks[j - 1])  # giu dau cau dinh sau token cuoi
            out.append(_vn_run_to_digits(run) + tail)
            i = j
        else:
            out.append(toks[i])
            i += 1
    return ' '.join(out)


def caption_display(text):
    """Transform text cho caption/hook hien thi (so + bo dau cau). KHONG dung cho TTS."""
    t = vn_numbers_to_digits(text)
    t = re.sub(r'[.,:;—–]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def generate_voice_per_scene(script_data, tmpdir):
    """Sinh voice voi SSML mark + timepoints de caption sync 100% chinh xac.

    Returns list of dict per scene:
        {"path": Path, "chunks": [...], "timepoints": [start_s of each chunk]}
    Timepoints are EXACT from Google TTS API - no heuristic.
    """
    voice_name = VOICES[datetime.now().day % len(VOICES)]
    print(f"[4/7] Generating voice per scene ({voice_name}) with SSML timepoints...")
    scene_meta = []
    for i, scene in enumerate(script_data["scenes"]):
        text = scene["voiceover"].strip()
        chunks = split_chunks_text(text, max_words=3)

        # Build SSML with marks between chunks: <mark name="c0"/>chunk0 <mark name="c1"/>chunk1 ...
        # XML escape Vietnamese text (safe for &, <, > - we already strip <>)
        ssml_parts = ['<speak>']
        for j, chunk in enumerate(chunks):
            ssml_parts.append(f'<mark name="c{j}"/>')
            ssml_parts.append(_html.escape(chunk, quote=False))
            ssml_parts.append(' ')
        ssml_parts.append('<mark name="cend"/>')
        ssml_parts.append('</speak>')
        ssml = "".join(ssml_parts)

        path = Path(tmpdir) / f"voice_{i}.mp3"
        # v1beta1 endpoint supports enableTimePointing (v1 does NOT)
        url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={GOOGLE_TTS_KEY}"
        body = {
            "input": {"ssml": ssml},
            "voice": {"languageCode": "vi-VN", "name": voice_name},
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.1,
                "pitch": 0.0,
                "volumeGainDb": 2.0,
                "sampleRateHertz": 24000,
                "effectsProfileId": ["small-bluetooth-speaker-class-device"],
            },
            "enableTimePointing": ["SSML_MARK"],
        }
        r = requests.post(url, json=body, timeout=60)
        if r.status_code != 200:
            print(f"      TTS API error scene {i+1}: {r.status_code} - {r.text[:200]}")
            r.raise_for_status()
        resp_json = r.json()
        audio_bytes = base64.b64decode(resp_json["audioContent"])
        with open(path, "wb") as f:
            f.write(audio_bytes)

        # Parse timepoints: list of {markName, timeSeconds}
        tps = resp_json.get("timepoints", [])
        tp_map = {tp["markName"]: tp["timeSeconds"] for tp in tps}
        # Build chunk_starts: c0_time, c1_time, ..., cend_time
        chunk_starts = [tp_map.get(f"c{j}", 0.0) for j in range(len(chunks))]
        chunk_end = tp_map.get("cend", 0.0)

        scene_meta.append({
            "path": path,
            "chunks": chunks,
            "chunk_starts": chunk_starts,
            "chunk_end": chunk_end,
        })
        if i == 0:
            print(f"      Scene 1 timepoints sample: {chunk_starts[:3]} ... end={chunk_end:.2f}s")

    print(f"      Generated {len(scene_meta)} voice files + timepoints")
    return scene_meta


# Backward compat name
def generate_voice(script_data, tmpdir):
    return generate_voice_per_scene(script_data, tmpdir)

# ==================== STEP 5: GHÉP VIDEO (MOVIEPY) ====================
def assemble_video(clip_paths, scene_voice_data, script_data, tmpdir):
    """Ghep clip + voice per scene + caption SYNC chinh xac voi voice.

    scene_voice_data: list of dict (from new TTS) HOAC list of Path (backward compat).
    """
    print("[5/7] Assembling video...")

    # Backward compat: if scene_voice_data is list of Paths, convert to dict format
    if scene_voice_data and isinstance(scene_voice_data[0], (str, Path)):
        scene_voice_data = [{"path": p, "chunks": None, "chunk_starts": None, "chunk_end": None}
                            for p in scene_voice_data]

    scene_voices = [AudioFileClip(str(d["path"])) for d in scene_voice_data]
    PAUSE = 0.2
    scene_durs = [v.duration + PAUSE for v in scene_voices]
    total_dur = sum(scene_durs)
    print(f"      Total duration: {total_dur:.1f}s ({len(scene_voices)} scenes)")

    # Build clips with matching per-scene durations
    # Force 24fps on ALL source clips de tranh fps mismatch giat khung hinh
    target_w, target_h = 1080, 1920
    TARGET_FPS = 24
    clips = []
    for i, (p, target_dur) in enumerate(zip(clip_paths, scene_durs)):
        c = VideoFileClip(str(p)).without_audio()
        # Normalize fps NGAY tu nguon de tranh stutter khi concat
        c = c.set_fps(TARGET_FPS)
        scale = max(target_w / c.w, target_h / c.h)
        c = c.resize(scale)
        c = c.crop(x_center=c.w/2, y_center=c.h/2, width=target_w, height=target_h)
        if c.duration < target_dur:
            # AI Ken Burns clip 10s should cover -> rarely loop. Pexels may.
            c = c.loop(duration=target_dur)
        else:
            c = c.subclip(0, target_dur)

        # iter 18: ZOOM-IN PUNCH last 0.4s (viral Shorts pacing effect)
        # Zoom 1.0 -> 1.12 in last 0.4s -> sharp visual pop at scene end
        _punch_dur = min(0.4, c.duration * 0.3)
        _clip_dur = c.duration
        def _zoom_punch_factory(clip_dur, punch_dur):
            def _zoom(t):
                if t < clip_dur - punch_dur:
                    return 1.0
                progress = max(0, (t - (clip_dur - punch_dur)) / punch_dur)
                return 1.0 + 0.12 * min(1.0, progress)
            return _zoom
        c = c.resize(_zoom_punch_factory(_clip_dur, _punch_dur))
        clips.append(c)

    video = concatenate_videoclips(clips, method="compose")

    # iter 18: COLOR GRADE BOOST — saturation cho pop visual
    # iter 18.1: 1.18 -> 1.10 (less aggressive, avoid oversaturated look)
    try:
        from moviepy.video.fx.colorx import colorx
        video = colorx(video, factor=1.10)
    except ImportError:
        pass

    # Build composite audio: voice scene 1 at t=0, scene 2 at t=dur1, ...
    from moviepy.editor import CompositeAudioClip
    audio_parts = []
    current_t = 0.0
    for v in scene_voices:
        audio_parts.append(v.set_start(current_t))
        current_t += v.duration + PAUSE  # gap silence

    # === BACKGROUND MUSIC ===
    # iter 20 (AI niche): UU TIEN nhac tech/electronic/upbeat -> nang dong, hop Shorts AI.
    # (truoc day logic bida loai bo cac track nay -> nghe cham/chan; nay dao lai.)
    all_bgm = list(BGM_DIR.glob("*.mp3")) if BGM_DIR.exists() else []
    # Blocklist track CHAM/buon (Kevin MacLeod cinematic) -> moi track con lai (gom nhac
    # ban tu drop vao sau) deu vao pool soi dong. Drop file bgm_18+.mp3 la tu dong duoc dung.
    _slow = ("backed_vibes", "inspired", "lobby_time", "carefree",
             "local_forecast", "investigations")
    energetic_bgm = [f for f in all_bgm if not any(k in f.name.lower() for k in _slow)]
    bgm_files = energetic_bgm if energetic_bgm else all_bgm
    bgm_filename_used = None  # Trace cho copyright claim
    if bgm_files:
        bgm_path = random.choice(bgm_files)
        bgm_filename_used = bgm_path.name
        print(f"      BGM: {bgm_path.name} (energetic pool: {len(energetic_bgm)}/{len(all_bgm)})")
        bgm = AudioFileClip(str(bgm_path)).volumex(0.16)
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
    # Uu tien: Be Vietnam Pro (Google Font designed cho Vietnamese, dau dep) ->
    #          Montserrat (TikTok aesthetic) -> Noto/DejaVu -> system default
    import os.path
    import glob as _glob
    _font_candidates = [
        # Montserrat Black (iter 19.1: user "font khac day hon" - geometric viral
        # Shorts aesthetic, weight 900, ho tro day du dau tieng Viet).
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/Montserrat-Black.ttf"),
        os.path.expanduser("~/Library/Fonts/Montserrat-Black.ttf"),
        "/tmp/fonts/Montserrat-Black.ttf",
        # Be Vietnam Pro Black (fallback - weight 900, Vietnamese-optimized)
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/BeVietnamPro-Black.ttf"),
        os.path.expanduser("~/Library/Fonts/BeVietnamPro-Black.ttf"),
        "/tmp/fonts/BeVietnamPro-Black.ttf",
        # Fallback ExtraBold neu Black khong co
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/BeVietnamPro-ExtraBold.ttf"),
        os.path.expanduser("~/Library/Fonts/BeVietnamPro-ExtraBold.ttf"),
        "/tmp/fonts/BeVietnamPro-ExtraBold.ttf",
        # GitHub Actions Montserrat fallback (downloaded vao /tmp/fonts/)
        "/tmp/fonts/Montserrat-Black.ttf",
        "/tmp/fonts/Montserrat-ExtraBold.ttf",
        # macOS Homebrew fonts
        "/opt/homebrew/share/fonts/Montserrat-ExtraBold.ttf",
        "/opt/homebrew/share/fonts/NotoSans-Bold.ttf",
        # macOS system fonts (built-in, support Vietnamese tot)
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Avenir Next.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        # User-installed Montserrat macOS
        os.path.expanduser("~/Library/Fonts/Montserrat-ExtraBold.ttf"),
        os.path.expanduser("~/Library/Fonts/NotoSans-Bold.ttf"),
        # Linux (GitHub Actions Ubuntu)
        "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Windows fallback Montserrat / system fonts
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/Montserrat-ExtraBold.ttf"),
        "C:/Windows/Fonts/Montserrat-ExtraBold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ]
    # Env override: CAPTION_FONT_PATH cho phep test font khac nhanh
    _caption_font_override = os.environ.get("CAPTION_FONT_PATH", "").strip()
    if _caption_font_override and os.path.exists(_caption_font_override):
        VN_FONT = _caption_font_override
    else:
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

    # Hook font rieng: uu tien Montserrat-ExtraBold (yellow + stroke render dung tren IM7)
    # BeVietnamPro Black + stroke day -> fill bi che, chu mat mau
    _hook_font_candidates = [
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/Montserrat-ExtraBold.ttf"),
        os.path.expanduser("~/Library/Fonts/Montserrat-ExtraBold.ttf"),
        "/tmp/fonts/Montserrat-ExtraBold.ttf",
        "/tmp/fonts/Montserrat-Black.ttf",
        "C:/Windows/Fonts/Montserrat-ExtraBold.ttf",
        "/opt/homebrew/share/fonts/Montserrat-ExtraBold.ttf",
    ]
    HOOK_FONT = next((p for p in _hook_font_candidates if os.path.exists(p)), VN_FONT)
    print(f"      Hook Font: {HOOK_FONT.split('/')[-1] if '/' in HOOK_FONT else HOOK_FONT}")

    # Disclaimer ALWAYS hien o top trong 4s dau
    disclaimer = (TextClip(DISCLAIMER_TEXT, fontsize=38, color="white",
                          bg_color="rgba(0,0,0,0.7)", size=(900, None),
                          method="caption", font=VN_FONT)
                  .set_position(("center", 100))
                  .set_start(0).set_duration(4))

    # === HOOK VISUAL — diem nhan 2s dau (TikTok/Shorts style) ===
    # Uu tien hook tu script JSON neu co, neu khong extract tu scene 1 voiceover
    hook_text_raw = script_data["scenes"][0]["voiceover"]
    hook_explicit = script_data.get("hook", "").strip()
    import re as _re
    if hook_explicit:
        hook_text = hook_explicit
    else:
        # Cat thong minh: thu lay cau ngan nhat ket thuc bang .?!
        # Sau do tu de;,. Tuong tu Shorts viral: ngan, manh, gay shock
        sentences = _re.split(r"(?<=[.?!])\s+", hook_text_raw.strip())
        hook_text = sentences[0] if sentences else hook_text_raw
        # Neu cau dau > 60 chars, cat o dau ; hoac dau ,
        if len(hook_text) > 60:
            for sep in [";", ","]:
                idx = hook_text.find(sep)
                if 20 <= idx <= 60:
                    hook_text = hook_text[:idx].strip()
                    break
        # Fallback cuoi: 8 tu dau + ...
        if len(hook_text) > 70:
            hook_text = " ".join(hook_text.split()[:8]) + "..."
    print(f"      Hook: \"{hook_text}\"")
    hook_display = caption_display(hook_text)  # iter 20: bo dau cau + so cho HIEN THI

    # Hook visual: TRANG + STROKE + BG SEMI-DEN (pill style)
    # iter 18: BIGGER fontsize (no resize animation - breaks IM stroke + fill)
    # iter 18.1: REVERT scale-pop, use fast fadein opacity (preserves text rendering)
    _hook_len = len(hook_display)
    if _hook_len <= 25:
        _hook_size = 145
    elif _hook_len <= 45:
        _hook_size = 125
    elif _hook_len <= 65:
        _hook_size = 105
    else:
        _hook_size = 92

    hook_visual = (TextClip(hook_display, fontsize=_hook_size, color="white",
                           stroke_color="black", stroke_width=5,
                           bg_color="rgba(0,0,0,0.72)",
                           size=(980, None), method="caption", font=HOOK_FONT)
                   .set_position(("center", 700))
                   .set_start(0).set_duration(2.8)
                   .fadein(0.12).fadeout(0.4))

    # === KARAOKE-STYLE CAPTIONS ===
    # Chia voiceover thanh cum sentences -> sub hien chinh xac voi thuyet minh
    def split_chunks(text, max_words=6):
        """Chia thanh cum 5-6 tu, uu tien ngat o dau cau de sub khop voice.
        Return list of chunks giu original text exact (TTS dung text nay).
        """
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

    def _normalize(s):
        """Lowercase + bo dau cau de match hook vs chunks."""
        out = s.lower()
        for ch in [".", ",", "!", "?", ";", ":"]:
            out = out.replace(ch, "")
        return " ".join(out.split())

    hook_norm = _normalize(hook_text) if hook_text else ""

    # CAPTION_LEAD: caption hien som hon voice 0.1s de compensate visual perception
    # (con offset nho - timepoints da chinh xac roi)
    CAPTION_LEAD = 0.1

    for i, scene in enumerate(script_data["scenes"]):
        voice_dur = scene_voices[i].duration
        # Get chunks + timepoints from TTS metadata (preferred) or fallback split
        scene_data = scene_voice_data[i]
        chunks = scene_data.get("chunks")
        chunk_starts_tp = scene_data.get("chunk_starts")
        chunk_end_tp = scene_data.get("chunk_end") or voice_dur
        if not chunks or not chunk_starts_tp:
            chunks = split_chunks(scene["voiceover"], max_words=3)
            chunk_starts_tp = None  # fallback heuristic
        if not chunks:
            start_t += scene_durs[i]
            continue

        # Scene 1: SKIP chunks da co trong hook (tranh repeat sub trung hook visual)
        skip_count = 0
        if i == 0 and hook_norm:
            accumulated = ""
            for j, chunk in enumerate(chunks):
                accumulated = (accumulated + " " + chunk).strip()
                acc_norm = _normalize(accumulated)
                if hook_norm in acc_norm:
                    skip_count = j + 1
                    break

        # Build chunk timing: use EXACT timepoints if available, else heuristic
        if chunk_starts_tp:
            # EXACT mode: caption at chunk_start[j] - LEAD, duration = next_start - this_start
            chunk_timings = []  # list of (abs_start, duration)
            for j in range(skip_count, len(chunks)):
                next_start = chunk_starts_tp[j+1] if j+1 < len(chunks) else chunk_end_tp
                abs_start = max(start_t, start_t + chunk_starts_tp[j] - CAPTION_LEAD)
                duration = max(0.3, next_start - chunk_starts_tp[j])
                chunk_timings.append((chunks[j], abs_start, duration))
        else:
            # FALLBACK heuristic (old logic)
            all_words = [max(1, len(c.split())) for c in chunks]
            total_words = sum(all_words)
            skipped_words = sum(all_words[:skip_count])
            chunks_render = chunks[skip_count:]
            if total_words:
                base_start = start_t + voice_dur * (skipped_words / total_words)
                cap_window_dur = voice_dur * (1 - skipped_words / total_words)
            else:
                base_start = start_t
                cap_window_dur = voice_dur
            cap_window_start = max(start_t, base_start - CAPTION_LEAD)
            render_words = [max(1, len(c.split())) for c in chunks_render]
            render_total = sum(render_words) or 1
            chunk_durs = [cap_window_dur * (w / render_total) * 0.92 for w in render_words]
            chunk_timings = []
            chunk_t = cap_window_start
            for j, chunk in enumerate(chunks_render):
                chunk_timings.append((chunk, chunk_t, chunk_durs[j]))
                chunk_t += chunk_durs[j]

        for chunk, chunk_t, chunk_dur in chunk_timings:
            # Caption: TRANG + STROKE 3 + SHADOW DEN OFFSET (look bold/3D)
            # Timing dung EXACT timepoints tu Google TTS SSML mark (sync 100%)
            # iter 20: caption_display -> bo dau cau . , : ; — + so bang chu thanh chu so
            chunk_disp = caption_display(chunk)
            if not chunk_disp:
                continue
            CHUNK_FONT = 85
            shadow = (TextClip(chunk_disp, fontsize=CHUNK_FONT, color="black",
                              size=(980, None), method="caption", font=VN_FONT)
                      .set_position(("center", 1287))
                      .set_start(chunk_t).set_duration(chunk_dur)
                      .fadein(0.06))
            cap = (TextClip(chunk_disp, fontsize=CHUNK_FONT, color="white",
                           stroke_color="black", stroke_width=3,
                           size=(980, None), method="caption", font=VN_FONT)
                   .set_position(("center", 1280))
                   .set_start(chunk_t).set_duration(chunk_dur)
                   .fadein(0.06))
            scene_captions.append(shadow)
            scene_captions.append(cap)
        start_t += scene_durs[i]

    # iter 20: WATERMARK handle @aimoingay.official goc duoi (chong repost + brand), suot video
    watermark = (TextClip("@aimoingay.official", fontsize=44, color="white",
                          stroke_color="black", stroke_width=1, font=VN_FONT)
                 .set_position((48, 1815))
                 .set_start(0).set_duration(total_dur)
                 .set_opacity(0.72))

    final = CompositeVideoClip([video, hook_visual, disclaimer] + scene_captions + [watermark])
    output = Path(tmpdir) / "final.mp4"

    # Memory + encoder optimization (29/05 — speedup 4x Windows, 2x Linux):
    # - gc.collect() truoc khi render de free temp arrays
    # - Windows: AMD GPU h264_amf encoder + threads=8 (i7-12700F 20T thua suc)
    # - Linux CI: libx264 + preset=veryfast + threads=4
    # - macOS: libx264 + medium (safer default)
    # - fps 30 -> 24 (-20% frames, YouTube Shorts native 24fps OK)
    import gc as _gc
    _gc.collect()

    import platform as _pl
    _sys = _pl.system()
    # LOCAL_FAST_MODE: ultrafast preset + bitrate thap (test_local --fast)
    # Note: bottleneck KHONG phai encoder ma la MoviePy Python compositing
    # -> tang threads/preset chi tiet kiem ~10-15%, khong giam dot bien
    # -> Toi uu lon hon can refactor sang FFmpeg native overlay filter
    _fast_mode = os.environ.get("LOCAL_FAST_MODE", "").lower() in ("1", "true", "yes")

    if _sys == "Windows":
        # Local Windows: libx264 ultrafast + 8 threads (i7 sufficient)
        _codec = "libx264"
        _threads = int(os.environ.get("FFMPEG_THREADS", "8"))
        _preset = os.environ.get("FFMPEG_PRESET", "ultrafast")
        _extra_params = []
    elif _sys == "Linux":
        # Linux (CI it nhan HOAC may local nhieu nhan): threads = so core that - 2.
        # CI 2-4 nhan -> ~4; may 20 nhan -> 16. Override qua FFMPEG_THREADS / FFMPEG_PRESET.
        _cores = os.cpu_count() or 4
        _codec = "libx264"
        _threads = int(os.environ.get("FFMPEG_THREADS", str(min(16, max(4, _cores - 2)))))
        _preset = os.environ.get("FFMPEG_PRESET", "veryfast")
        _extra_params = []
        print(f"      [encode] Linux {_cores} core -> {_threads} threads, preset {_preset}")
    else:  # macOS hoac OS khac
        _codec, _threads, _preset = "libx264", 4, "medium"
        _extra_params = []

    # Bitrate: fast mode dung 3500k (preview), production 8000k (iter 20: tang net cho Shorts 1080x1920)
    _bitrate = "3500k" if _fast_mode else "8000k"
    if _fast_mode:
        print(f"      [LOCAL_FAST_MODE] bitrate {_bitrate} + preset {_preset}")

    def _do_write(out_path, codec, threads, preset, bitrate, extra=None,
                  tmp_audio="temp_audio.m4a"):
        final.write_videofile(
            str(out_path),
            fps=24,
            codec=codec,
            audio_codec="aac",
            preset=preset,
            bitrate=bitrate,
            audio_bitrate="192k",
            threads=threads,
            temp_audiofile=str(Path(tmpdir) / tmp_audio),
            remove_temp=True,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"] + (extra or []),
            verbose=False,
            logger=None,
        )

    try:
        try:
            _do_write(output, _codec, _threads, _preset, _bitrate, _extra_params)
        except Exception as enc_e:
            # Encoder loi (h264_amf khong support hoac driver issue) -> fallback libx264
            err_str = str(enc_e).lower()
            if _codec != "libx264" and any(k in err_str for k in ["encoder", "amf", "nvenc", "codec"]):
                print(f"      ⚠ {_codec} fail ({enc_e}) - fallback libx264 veryfast")
                _gc.collect()
                _do_write(output, "libx264", 8 if _sys == "Windows" else 4, "veryfast", _bitrate, [])
            else:
                raise
    except (MemoryError, Exception) as e:
        # Fallback: neu MemoryError -> retry voi resolution 720x1280 (con 56% memory)
        if "MemoryError" in type(e).__name__ or "allocate" in str(e):
            print(f"      ⚠ Memory tight, retry voi 720x1280 libx264...")
            _gc.collect()
            final_lo = final.resize((720, 1280))
            final_lo.write_videofile(
                str(output),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                preset="veryfast",
                bitrate="3500k",
                audio_bitrate="192k",
                threads=4,
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
    # Return tuple (path, bgm_filename) - bgm dùng để log vào published.json cho trace copyright
    return output, bgm_filename_used

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


def next_publish_slot():
    """Moc publish ke tiep: 05:00 hoac 13:00 UTC (= 12:00/20:00 gio VN), strictly sau now+10p.
    Dung cho scheduled-publish -> video tu cong khai dung gio du cron GitHub chay tre."""
    now = datetime.now(timezone.utc)
    cands = []
    for off in (0, 1):
        base = (now + timedelta(days=off)).replace(minute=0, second=0, microsecond=0)
        for h in (5, 13):
            c = base.replace(hour=h)
            if c > now + timedelta(minutes=10):
                cands.append(c)
    return min(cands)


def upload_to_youtube(video_path, script_data, idea):
    """Upload video lên YouTube với metadata đầy đủ + credit nhạc CC-BY."""
    print("[6/7] Uploading to YouTube...")
    yt = get_youtube_service()

    # Description niche AI (AI Mỗi Ngày) + Kevin MacLeod CC-BY music credit (BẮT BUỘC)
    full_desc = (
        f"{script_data['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎵 Nhạc: Kevin MacLeod (incompetech.com) — Creative Commons BY 4.0\n"
        f"https://creativecommons.org/licenses/by/4.0/\n\n"
        f"⚠️ Nội dung chia sẻ kinh nghiệm sử dụng công cụ AI. Hình minh họa tạo bằng AI. "
        f"Tên sản phẩm thuộc về chủ sở hữu tương ứng.\n"
        f"📧 Liên hệ: aimoingay.contact@gmail.com"
    )
    # YouTube reject description chứa ký tự < hoặc > (HTML injection risk).
    # Replace ngay đây trước khi build body — defense-in-depth dù scripts đã clean.
    full_desc = full_desc.replace("<", "‹").replace(">", "›")
    safe_title = script_data["title"][:100].replace("<", "‹").replace(">", "›")

    # Status: YT_SCHEDULE=1 -> upload PRIVATE + publishAt moc 12:00/20:00 VN ke tiep
    # (YouTube tu cong khai dung gio, chinh xac hon cron GitHub hay tre).
    # Nguoc lai -> dung YT_PRIVACY ngay (public/unlisted/private) cho test/manual.
    if os.environ.get("YT_SCHEDULE", "").lower() in ("1", "true", "yes"):
        _slot = next_publish_slot()
        _status = {
            "privacyStatus": "private",
            "publishAt": _slot.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        }
        print(f"      Scheduled publish: tự công khai lúc {_slot.strftime('%Y-%m-%d %H:%M')} UTC "
              f"(= {(_slot + timedelta(hours=7)).strftime('%H:%M')} VN)")
    else:
        _status = {
            "privacyStatus": os.environ.get("YT_PRIVACY", "public"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        }

    body = {
        "snippet": {
            "title": safe_title,  # YouTube giới hạn 100 + strip <>
            "description": full_desc[:5000],
            "tags": script_data.get("tags", [])[:30],
            "categoryId": "28",  # Science & Technology (niche AI)
            "defaultLanguage": "vi",
            "defaultAudioLanguage": "vi",
        },
        "status": _status,
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
        clip_paths = fetch_all_clips(script_data["scenes"], tmpdir, idea_id=idea["id"])
        scene_voice_paths = generate_voice_per_scene(script_data, tmpdir)
        video_path, bgm_file = assemble_video(clip_paths, scene_voice_paths, script_data, tmpdir)
        # 6. Upload
        video_id = upload_to_youtube(video_path, script_data, idea)

    # 7. Log (kèm bgm_file để trace nếu video bị Content ID claim sau)
    mark_published(ideas, idea["id"], video_id, bgm_file=bgm_file)
    print("[7/7] Logged to published.json")
    print("=" * 60)
    print(f"Done! Video: https://youtube.com/watch?v={video_id}")
    print("=" * 60)

if __name__ == "__main__":
    main()
