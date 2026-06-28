"""Standalone upload — dung video local da render xong + script JSON metadata.

Usage:
    cd github_repo
    python pipeline/upload_only.py --id 18 --video test_output/video_18_xxx.mp4

Khong re-render, chi upload + update published.json.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "data" / "scripts"
PUBLISHED_FILE = REPO_ROOT / "data" / "published.json"


def load_dotenv_if_exists():
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True, help="Idea ID")
    parser.add_argument("--video", type=str, required=True, help="Path to mp4 file")
    parser.add_argument("--privacy", type=str, default=None,
                        help="Override YT_PRIVACY (default env or 'public')")
    args = parser.parse_args()

    load_dotenv_if_exists()
    if args.privacy:
        os.environ["YT_PRIVACY"] = args.privacy

    # Verify
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    script_path = SCRIPTS_DIR / f"{args.id}.json"
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    print(f"Title: {script_data['title']}")
    print(f"Video: {video_path} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Privacy: {os.environ.get('YT_PRIVACY', 'public')}")

    from main import upload_to_youtube
    idea = {"id": args.id, "title": script_data["title"], "pillar": "saving"}
    video_id = upload_to_youtube(str(video_path), script_data, idea)

    # Update published.json (cross-platform: utf-8-sig de chiu BOM, ghi bang json.dump)
    published = []
    if PUBLISHED_FILE.exists():
        with open(PUBLISHED_FILE, "r", encoding="utf-8-sig") as f:
            published = json.load(f)
    published.append({
        "idea_id": args.id,
        "video_id": video_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump(published, f, ensure_ascii=False, indent=2)

    print(f"DONE. https://youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
