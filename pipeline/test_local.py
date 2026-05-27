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


def ensure_montserrat_font():
    """Auto-download Montserrat ve ~/Library/Fonts/ neu chua co (macOS).

    Pipeline can font Unicode dep cho caption Vietnamese. Mac built-in
    co Helvetica/Arial nhung khong dep bang Montserrat (TikTok style).
    """
    import platform
    if platform.system() != "Darwin":
        return  # Chi auto-cai tren macOS, Linux/Win bo qua
    target_dir = Path.home() / "Library" / "Fonts"
    target_file = target_dir / "Montserrat-ExtraBold.ttf"
    if target_file.exists():
        print(f"✅ Montserrat: ~/Library/Fonts/Montserrat-ExtraBold.ttf")
        return
    print(f"⏬ Downloading Montserrat-ExtraBold to ~/Library/Fonts/ ...")
    target_dir.mkdir(parents=True, exist_ok=True)
    import urllib.request
    url = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
           "montserrat/static/Montserrat-ExtraBold.ttf")
    try:
        urllib.request.urlretrieve(url, str(target_file))
        size_kb = target_file.stat().st_size // 1024
        if size_kb < 50:  # File font that thuong >100KB
            target_file.unlink()
            print(f"⚠ Download fail (size={size_kb}KB), fallback dung system font")
        else:
            print(f"✅ Montserrat installed ({size_kb}KB)")
    except Exception as e:
        print(f"⚠ Khong tai duoc Montserrat ({e}), fallback dung system font")


def check_prereqs(skip_tts: bool):
    """Kiem tra deps + env vars truoc khi chay."""
    issues = []

    # 1. ffmpeg
    if not shutil.which("ffmpeg"):
        issues.append("❌ ffmpeg KHONG tim thay. Cai: brew install ffmpeg")
    else:
        print(f"✅ ffmpeg: {shutil.which('ffmpeg')}")

    # 2. ImageMagick convert (can cho TextClip caption)
    # IMv7 dung 'magick', IMv6 dung 'convert'. Brew install ca 2 alias.
    convert_path = shutil.which("convert") or shutil.which("magick")
    if not convert_path:
        issues.append("❌ ImageMagick KHONG tim thay. Cai: brew install imagemagick")
    else:
        print(f"✅ imagemagick: {convert_path}")

    # 3. Font Vietnamese (auto-download Montserrat tren Mac)
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
        video_path = assemble_video(clip_paths, scene_voice_paths, script_data, tmpdir_str)

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
            cleanup.cleanup()


if __name__ == "__main__":
    main()
