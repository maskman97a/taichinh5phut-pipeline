# Tài Chính 5 Phút — Pipeline tự động

Pipeline AI 100% tự động cho kênh YouTube Shorts về tài chính cá nhân + AI.

## Stack (100% Free)
- **GitHub Actions** — Orchestrator + cron daily
- **Google Gemini API** — Sinh script tiếng Việt
- **Pexels API** — Stock footage hợp pháp
- **Microsoft Edge TTS** — Voice tiếng Việt (vi-VN-HoaiMy, vi-VN-NamMinh)
- **MoviePy + FFmpeg** — Ghép video + caption
- **YouTube Data API v3** — Auto upload

## Chạy hằng ngày
06:00 sáng giờ Việt Nam (= 23:00 UTC ngày hôm trước)

## Cấu trúc
```
.
├── .github/workflows/daily.yml   # Cron + workflow steps
├── pipeline/
│   └── main.py                    # Pipeline orchestrator
├── data/
│   ├── ideas.json                 # Bank ý tưởng video (queue)
│   └── published.json             # Log video đã đăng
├── requirements.txt
└── README.md
```

## Test thủ công
Vào tab **Actions** → workflow "Daily YouTube Pipeline" → **Run workflow**

## Thêm ý tưởng mới
Edit `data/ideas.json` → add object mới với `"status": "todo"`

## Disclaimer
Nội dung video chỉ mang tính giáo dục, không phải lời khuyên đầu tư.
