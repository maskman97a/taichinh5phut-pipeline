"""
Test local — generate 1 video tu data/scripts/{id}.json, KHONG upload YouTube.

Output luu vao ./test_output/video_{id}_{timestamp}.mp4 de ban xem bang QuickTime/VLC.

Yeu cau:
- PEXELS_API_KEY + GOOGLE_TTS_API_KEY (export shell or .env)
- ffmpeg + imagemagick cai san (macOS: brew install ffmpeg imagemagick)
- pip install -r requirements.txt

Cach chay:
    cd github_repo
    export PEXELS_API_KEY=xxx
    export GOOGLE_TTS_API_KEY=xxx
    python pipeline/test_local.py --id 6
    python pipeline/test_local.py --id 6 --keep-tmp   # giu file tam de debug
    python pipeline/test_local.py --id 6 --skip-tts   # nhanh, video silent
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Them pipeline/ vao path de import main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "test_output"
SCRIPTS_DIR = REPO_ROOT / "data" / "scripts"


def load_dotenv_if_exists():
    """Auto-load .env file o repo root (KEY=VALUE per line).

    Khong dung python-dotenv (de tranh them dependency). Parser cuc don gian:
    - Bo qua comment (#) va dong rong
    - Strip quotes (' ho "...")
    - KHONG override env var da set san trong shell
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    loaded = []
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    if loaded:
        print(f"✅ .env loaded: {', '.join(loaded)}")


def ensure_montserrat_font():
    """Auto-download Montserrat ve folder font user (macOS + Windows).

    Pipeline can font Unicode dep cho caption Vietnamese. System font
    co Helvetica/Arial nhung khong dep bang Montserrat (TikTok style).
    """
    import platform
    system = platform.system()
    if system == "Darwin":
        target_dir = Path.home() / "Library" / "Fonts"
        nice_path = "~/Library/Fonts/Montserrat-ExtraBold.ttf"
    elif system == "Windows":
        # Per-user Windows fonts folder (khong can admin)
        target_dir = Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"
        nice_path = "%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts\\Montserrat-ExtraBold.ttf"
    else:
        return  # Linux: bo qua, dung font he thong
    target_file = target_dir / "Montserrat-ExtraBold.ttf"
    if target_file.exists():
        print(f"✅ Montserrat: {nice_path}")
        return
    print(f"⏬ Downloading Montserrat-ExtraBold to {nice_path} ...")
    target_dir.mkdir(parents=True, exist_ok=True)
    import urllib.request
    # Multiple mirrors (Google Fonts da restructure folder static/ -> fallback nhieu nguon)
    urls = [
        # Mirror 1: JulietaUla/Montserrat (upstream cua Google Fonts)
        "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
        # Mirror 2: jsDelivr CDN cua Google Fonts repo
        "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/montserrat/static/Montserrat-ExtraBold.ttf",
        # Mirror 3: Google Fonts repo direct (URL co the moved)
        "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/static/Montserrat-ExtraBold.ttf",
    ]
    last_err = None
    for url in urls:
        try:
            urllib.request.urlretrieve(url, str(target_file))
            size_kb = target_file.stat().st_size // 1024
            if size_kb >= 50:  # File font that thuong >100KB
                print(f"✅ Montserrat installed ({size_kb}KB)")
                return
            target_file.unlink()
            last_err = f"size={size_kb}KB qua nho"
        except Exception as e:
            last_err = str(e)
            continue
    print(f"⚠ Khong tai duoc Montserrat ({last_err}), fallback dung system font (Arial Bold)")


def check_prereqs(skip_tts: bool):
    """Kiem tra deps + env vars truoc khi chay."""
    # Load .env neu co (truoc khi check env vars)
    load_dotenv_if_exists()

    issues = []

    import platform as _plat
    _is_win = _plat.system() == "Windows"
    _ffmpeg_hint = (
        "winget install Gyan.FFmpeg" if _is_win else "brew install ffmpeg"
    )
    _im_hint = (
        "winget install ImageMagick.ImageMagick" if _is_win else "brew install imagemagick"
    )

    # 1. ffmpeg
    if not shutil.which("ffmpeg"):
        issues.append(f"❌ ffmpeg KHONG tim thay. Cai: {_ffmpeg_hint}")
    else:
        print(f"✅ ffmpeg: {shutil.which('ffmpeg')}")

    # 2. ImageMagick convert (can cho TextClip caption)
    # IMv7 dung 'magick', IMv6 dung 'convert'. Windows co 'convert.exe' rieng o
    # System32 (utility FAT->NTFS, KHONG PHAI ImageMagick) -> phai loai tru!
    convert_path = shutil.which("magick")
    if not convert_path and not _is_win:
        # Linux/Mac: 'convert' la safe alias cua ImageMagick
        convert_path = shutil.which("convert")
    if not convert_path and _is_win:
        # Windows: tim trong cac install path pho bien
        import glob as _glob
        for pattern in [
            r"C:\Program Files\ImageMagick-*\magick.exe",
            r"C:\Program Files (x86)\ImageMagick-*\magick.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\ImageMagick\magick.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\ImageMagick.ImageMagick*\magick.exe"),
        ]:
            matches = _glob.glob(pattern)
            if matches:
                convert_path = matches[0]
                break
    if not convert_path:
        issues.append(f"❌ ImageMagick KHONG tim thay. Cai: {_im_hint}")
        if _is_win:
            issues.append(
                "   (Windows: 'convert.exe' o System32 KHONG phai ImageMagick. "
                "Can cai IM v7 tu winget va dam bao co magick.exe trong PATH)"
            )
    else:
        print(f"✅ imagemagick: {convert_path}")
        # Windows: ep MoviePy dung magick.exe (IM v7) qua env var
        if _is_win:
            os.environ["IMAGEMAGICK_BINARY"] = convert_path

    # 3. Font Vietnamese (auto-download Montserrat tren Mac + Windows)
    ensure_montserrat_font()

    # 3. Env vars
    if not os.environ.get("PEXELS_API_KEY"):
        issues.append("❌ PEXELS_API_KEY chua set. Lay tai pexels.com/api")
    else:
        print(f"✅ PEXELS_API_KEY: ***{os.environ['PEXELS_API_KEY'][-4:]}")

    if not skip_tts and not os.environ.get("GOOGLE_TTS_API_KEY"):
        issues.append(
            "❌ GOOGLE_TTS_API_KEY chua set. Lay tai console.cloud.google.com "
            "(hoac chay voi --skip-tts de bo qua)"
        )
    elif not skip_tts:
        print(f"✅ GOOGLE_TTS_API_KEY: ***{os.environ['GOOGLE_TTS_API_KEY'][-4:]}")

    # 4. Python deps
    try:
        import requests  # noqa
        import moviepy  # noqa
        print(f"✅ python deps OK (moviepy, requests)")
    except ImportError as e:
        issues.append(f"❌ Python deps thieu: {e}. Chay: pip install -r requirements.txt")

    if issues:
        print("\n=== LOI PRE-REQS ===")
        for i in issues:
            print(i)
        sys.exit(1)


def generate_silent_voice(script_data, tmpdir):
    """Sinh file MP3 silent 4s/scene cho mode --skip-tts."""
    import subprocess
    paths = []
    for i in range(len(script_data["scenes"])):
        path = Path(tmpdir) / f"voice_{i}.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", "4", "-acodec", "libmp3lame", str(path)],
            check=True, capture_output=True
        )
        paths.append(path)
    print(f"[4/7] Sinh {len(paths)} silent voice files (skip-tts mode)")
    return paths


def main():
    parser = argparse.ArgumentParser(description="Test pipeline local — 1 video, no upload")
    parser.add_argument("--id", type=int, default=6,
                        help="Idea ID de test (default: 6 = Buffett Coca-Cola)")
    parser.add_argument("--skip-tts", action="store_true",
                        help="Bo qua Google TTS, dung silent audio (test nhanh)")
    parser.add_argument("--keep-tmp", action="store_true",
                        help="Giu thu muc tam sau khi xong (de debug)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"🧪 TEST LOCAL — Idea ID: {args.id}")
    print(f"   Mode: {'silent (skip TTS)' if args.skip_tts else 'full pipeline'}")
    print("=" * 60)

    # Pre-reqs
    print("\n--- Step 0: Check pre-reqs ---")
    check_prereqs(args.skip_tts)

    # Import main (sau khi check OK)
    print("\n--- Step 1: Import pipeline ---")
    try:
        from main import (
            load_script, fetch_all_clips, generate_voice_per_scene,
            assemble_video, BGM_DIR
        )
    except Exception as e:
        print(f"❌ Import main.py loi: {e}")
        sys.exit(1)
    print("✅ Import OK")

    # Load script
    print(f"\n--- Step 2: Load script idea {args.id} ---")
    script_path = SCRIPTS_DIR / f"{args.id}.json"
    if not script_path.exists():
        print(f"❌ Khong tim thay {script_path}")
        print(f"   Co {len(list(SCRIPTS_DIR.glob('*.json')))} script trong data/scripts/")
        sys.exit(1)

    idea = {"id": args.id, "title": f"test_idea_{args.id}", "pillar": "test"}
    script_data = load_script(idea)
    print(f"   Title: {script_data['title']}")
    print(f"   Scenes: {len(script_data['scenes'])}")

    # Setup output dir
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Tmp dir (persistent neu --keep-tmp)
    if args.keep_tmp:
        tmpdir = OUTPUT_DIR / f"tmp_{args.id}_{ts}"
        tmpdir.mkdir(exist_ok=True)
        tmpdir_str = str(tmpdir)
        print(f"\n[tmp giu lai] {tmpdir}")
        cleanup = None
    else:
        # ignore_cleanup_errors: Windows hay khong release file handles tu MoviePy/imageio,
        # khien rmtree fail. Khong nghiem trong (Windows tu don sau), nhung neu khong ignore
        # se nuot mat loi goc.
        try:
            _tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        except TypeError:
            # Python <3.10 khong support ignore_cleanup_errors
            _tmp = tempfile.TemporaryDirectory()
        tmpdir_str = _tmp.name
        cleanup = _tmp

    t0 = time.time()
    try:
        # Step 3: Download Pexels
        print(f"\n--- Step 3: Download Pexels clips ---")
        clip_paths = fetch_all_clips(script_data["scenes"], tmpdir_str)
        ok_count = sum(1 for p in clip_paths if p is not None)
        print(f"   Downloaded: {ok_count}/{len(clip_paths)} clips")
        if ok_count == 0:
            print("❌ Khong tai duoc clip nao - check PEXELS_API_KEY")
            sys.exit(1)

        # Step 4: TTS (hoac silent)
        print(f"\n--- Step 4: Generate voice ---")
        if args.skip_tts:
            scene_voice_paths = generate_silent_voice(script_data, tmpdir_str)
        else:
            scene_voice_paths = generate_voice_per_scene(script_data, tmpdir_str)

        # Step 5: Assemble video
        print(f"\n--- Step 5: Assemble video (MoviePy) ---")
        video_path, bgm_file = assemble_video(clip_paths, scene_voice_paths, script_data, tmpdir_str)
        if bgm_file:
            print(f"   BGM used: {bgm_file}")

        # Copy ra output dir (tmp se bi xoa)
        final = OUTPUT_DIR / f"video_{args.id}_{ts}.mp4"
        shutil.copy(str(video_path), str(final))

        elapsed = time.time() - t0
        size_mb = final.stat().st_size / 1024 / 1024
        print("\n" + "=" * 60)
        print(f"✅ DONE in {elapsed:.1f}s")
        print(f"   Video: {final}")
        print(f"   Size:  {size_mb:.1f} MB")
        print(f"\n   Mo bang: open {final}")
        print(f"   Hoac:    open -a 'QuickTime Player' {final}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ LOI: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if cleanup:
            try:
                cleanup.cleanup()
            except (PermissionError, OSError) as cleanup_err:
                # Windows: file handles MoviePy chua release. Bo qua, video da copy ra OK.
                print(f"⚠ Cleanup tmp folder fail (khong nghiem trong): {cleanup_err}")


if __name__ == "__main__":
    main()
