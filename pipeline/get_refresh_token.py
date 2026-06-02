"""OAuth 2.0 Refresh Token getter for YouTube Data API.

Chay 1 lan khi setup channel moi (vd: @aitoolsdaily). Sau khi co refresh token,
add vao GitHub Secrets va KHONG can chay lai.

Flow:
1. Hoi nhap Client ID + Client Secret (lay tu Google Cloud Console)
2. Open browser → user login Google account chua channel can upload
3. User approve "AI Tools Daily Pipeline" access (scope: youtube.upload)
4. Local HTTP server nhan callback → exchange code → refresh token
5. Print refresh token de user copy vao GitHub Secrets

Usage:
    cd github_repo
    .venv\\Scripts\\python.exe pipeline\\get_refresh_token.py

Requires: google-auth-oauthlib (da co trong requirements.txt)
"""

import sys
import os
from pathlib import Path

# Ensure deps available (already in requirements.txt)
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: google-auth-oauthlib chua cai. Chay: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    print("=" * 60)
    print("YouTube OAuth Refresh Token Getter")
    print("=" * 60)
    print()
    print("LAY Client ID + Client Secret tu Google Cloud Console:")
    print("  1. https://console.cloud.google.com")
    print("  2. Project: aitoolsdaily-pipeline (hoac project cua ban)")
    print("  3. APIs & Services -> Credentials")
    print("  4. OAuth 2.0 Client IDs -> click vao client desktop app")
    print("  5. Copy 'Client ID' + 'Client secret'")
    print()

    client_id = input("Client ID: ").strip()
    if not client_id:
        print("Client ID empty - abort")
        sys.exit(1)
    client_secret = input("Client Secret: ").strip()
    if not client_secret:
        print("Client Secret empty - abort")
        sys.exit(1)

    # Build OAuth flow
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print()
    print("Mo browser de ban login Google + approve access...")
    print("LUU Y: login bang account chua channel @aitoolsdaily")
    print()
    creds = flow.run_local_server(port=0, prompt="consent")

    refresh_token = creds.refresh_token
    if not refresh_token:
        print()
        print("ERROR: KHONG nhan duoc refresh_token!")
        print("  Likely cause: account da approve truoc do.")
        print("  Fix: vao https://myaccount.google.com/permissions")
        print("       -> revoke 'AI Tools Daily Pipeline' -> chay lai script")
        sys.exit(1)

    print()
    print("=" * 60)
    print("SUCCESS! 3 values can add vao GitHub Secrets:")
    print("=" * 60)
    print()
    print(f"YT_CLIENT_ID:")
    print(f"  {client_id}")
    print()
    print(f"YT_CLIENT_SECRET:")
    print(f"  {client_secret}")
    print()
    print(f"YT_REFRESH_TOKEN:")
    print(f"  {refresh_token}")
    print()
    print("=" * 60)
    print()
    print("BUOC TIEP THEO:")
    print("  1. Vao https://github.com/maskman97a/taichinh5phut-pipeline/settings/secrets/actions")
    print("  2. Update 3 secrets tren")
    print("  3. KHONG share refresh_token!")
    print("  4. Resume cron: uncomment schedule trong .github/workflows/daily.yml")
    print()

    # Optional: save to local .env (gitignored)
    save = input("Save vao github_repo/.env (gitignored) khong? [y/N]: ").strip().lower()
    if save == "y":
        env_path = Path(__file__).resolve().parent.parent / ".env"
        existing = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition("=")
                    existing[k.strip()] = v.strip()
        existing["YT_CLIENT_ID"] = client_id
        existing["YT_CLIENT_SECRET"] = client_secret
        existing["YT_REFRESH_TOKEN"] = refresh_token
        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Saved to {env_path}")
        print("Local upload bay gio works qua test_local.py.")


if __name__ == "__main__":
    main()
