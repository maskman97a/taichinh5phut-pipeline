# AI Mỗi Ngày — Pipeline tự động

Pipeline AI tự động cho kênh YouTube Shorts **AI Mỗi Ngày**: tự động hóa + mẹo dùng AI trong đời sống (tiếng Việt). Mỗi ngày tự render + upload 2 video.

## Stack (100% free)
- **GitHub Actions** — orchestrator + cron 2 lần/ngày
- **Script pre-gen** — script JSON viết sẵn trong `data/scripts/` (không gọi LLM API lúc chạy)
- **Pollinations Flux** — sinh ảnh AI (hero shot trừu tượng) + **Pexels** stock footage thật
- **Google Cloud TTS** — voice vi-VN (Neural2/Wavenet, rotate nam/nữ) + SSML timepoints sync caption
- **MoviePy + FFmpeg + ImageMagick** — ghép video, Ken Burns, caption karaoke
- **YouTube Data API v3** — auto upload

## Lịch chạy
**12:00 trưa & 20:00 tối giờ VN** mỗi ngày (= 05:00 & 13:00 UTC). Mỗi lần 1 video (idea `todo` kế tiếp).

## Cấu trúc
```
.
├── .github/workflows/daily.yml   # Cron + steps (cài ffmpeg/imagemagick/fonts, chạy pipeline)
├── VIRAL_PLAYBOOK.md             # Luật viết script + caption + không lặp content
├── pipeline/
│   ├── main.py                   # Orchestrator (render + upload)
│   ├── test_local.py             # Render thử local (không upload)
│   └── upload_only.py            # Upload mp4 có sẵn
├── data/
│   ├── ideas.json                # Queue ý tưởng
│   ├── scripts/{id}.json         # Script từng video
│   ├── published.json            # Log đã đăng
│   └── used_pexels.json          # Dedup footage xuyên video
├── audio/                        # BGM (tech/electronic, CC)
└── requirements.txt
```

## Quy tắc nội dung
Xem `VIRAL_PLAYBOOK.md`: hook xoay 5 công thức, 11 cảnh pace nhanh, re-hook + open loop, **không lặp content**, caption bỏ dấu câu + số dạng chữ số, ảnh AI chỉ cho hero shot trừu tượng (còn lại footage thật).

## Test thủ công
Tab **Actions** → "Daily YouTube Pipeline" → **Run workflow**.

## Thêm ý tưởng
Thêm object vào `data/ideas.json` (`"status": "todo"`) + viết `data/scripts/{id}.json` theo VIRAL_PLAYBOOK.

## Disclaimer
Nội dung chia sẻ kinh nghiệm dùng công cụ AI. Hình minh họa tạo bằng AI. Nhạc: Kevin MacLeod (CC BY 4.0).
