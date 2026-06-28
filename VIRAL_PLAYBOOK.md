# VIRAL PLAYBOOK — Shorts AI Tips (VN)

> Bộ luật viết script + dựng video, rút từ nghiên cứu pattern viral Shorts 2026 (faceless/AI niche).
> ĐỌC TRƯỚC mỗi lần gen script `data/scripts/{id}.json`. Nguồn ở cuối file.

---

## ⛔ RULE #0 — KHÔNG ĐƯỢC LẶP LẠI CONTENT (quan trọng nhất)

Mỗi video phải KHÁC BIỆT hoàn toàn. Cấm lặp ở mọi tầng:

| Tầng | Cấm | Bắt buộc |
|---|---|---|
| **Ý tưởng** | 2 video cùng công cụ/cùng tác vụ | Mỗi video 1 tool + 1 use-case riêng |
| **Hook** | Dùng lại câu mở / cùng 1 công thức hook 2 lần liên tiếp | Xoay vòng 5 công thức hook (mục 2) |
| **Mở đầu** | Lặp cấu trúc câu "Bạn không cần..." nhiều lần | Đổi kiểu mở mỗi video |
| **CTA** | Cùng 1 câu kêu gọi đăng ký | Viết lại CTA mỗi video |
| **Footage** | Trùng clip Pexels | TỰ ĐỘNG chặn qua `data/used_pexels.json` (cross-video dedup) |
| **Tool tfeatures** | Lặp tool quá 1 lần/5 video | Rotate: LLM → IDE/app → image → workflow → so sánh |

Trước khi viết script mới: đọc các script đã có trong `data/scripts/` + `data/published.json` để chắc chắn không trùng hook/tool/use-case.

---

## 1. CẤU TRÚC VIDEO (45-55s, pace nhanh)

- **10-12 scene** (KHÔNG phải 8) — cảnh ngắn 3-4s → cắt nhanh, ít "dead air". 72% Shorts >1M view dùng pace nhanh.
- Câu thoại NGẮN, present tense, động từ mạnh. Mỗi cảnh 1 ý.
- Khung xương: **Hook (0-3s) → Vấn đề (1 cảnh) → Giải pháp → Demo từng bước (3-5 cảnh ngắn) → Kết quả/số liệu → Re-hook giữa → Bonus → CTA + open loop**.
- **Re-hook ở ~15-20s**: 1 câu tạo tò mò mới ("Nhưng đây mới là phần hay nhất..." / "Còn 1 mẹo ít người biết...") để chống tụt retention giữa video.
- **Open loop ở cuối**: tạo lý do xem hết / xem lại ("Mẹo cuối mới là thứ thay đổi mọi thứ").

## 2. HOOK (3 giây đầu — yếu tố #1)

- Từ đầu tiên phải vang trong **0.5s** (lead 0.25s đã có). KHÔNG intro, KHÔNG "xin chào".
- Hook = câu thoại scene 1, hiện luôn dạng text overlay (đã làm). Mục tiêu "Viewed vs Swiped Away" ≥ 70%.
- **Xoay vòng 5 công thức** (mỗi video chọn 1 khác lần trước):
  1. **Tuyên bố táo bạo:** "Hầu hết mọi người không biết [tool] làm được [điều này]."
  2. **Khoảng trống tò mò:** "Có một cách dùng [tool] mà chẳng ai nói cho bạn."
  3. **Micro-story:** "Tôi tiết kiệm 2 tiếng mỗi ngày chỉ nhờ một mẹo AI này."
  4. **Sốc thị giác/số liệu:** mở bằng con số to / before-after ("10 giây thay vì 1 tiếng").
  5. **Câu hỏi trực diện:** "Bạn còn ngồi gõ tay việc này à? AI làm xong trong 5 giây."
- Cấm dùng "Trong video này tôi sẽ...", "Hôm nay mình...".

## 3. HÌNH ẢNH (xem [[visual-quality-rules]])

- **AI gen CHỈ cho hero shot trừu tượng** (icon/nút phát sáng, tech abstract). KHÔNG dùng AI cho màn hình/UI/chữ (ra chữ nhòe giả → rẻ tiền).
- **Footage thật Pexels** cho người/thiết bị/thao tác/màn hình → premium.
- Ưu tiên đa số footage thật. Mở đầu = frame ấn tượng nhất video.
- Cân nhắc thêm `asian` vào keyword người để gần gũi khán giả Việt.
- Pattern interrupt trong 5s đầu (+23% retention). Đổi hình mỗi 3-4s.
- **Loop**: cảnh cuối nên "vần" thị giác với cảnh đầu để xem lại liền mạch (mỗi loop tính 1 view từ 2025).

## 4. CAPTION & ÂM THANH

- Caption karaoke từ chữ đầu tiên (đã có) — 85% xem KHÔNG tiếng → phải đọc hiểu khi tắt loa.
- **Caption KHÔNG có dấu câu** `.` `,` `:` `;` `—` `–` (tự động bỏ bởi `caption_display()` — chỉ ảnh hưởng hiển thị, giọng TTS giữ nguyên).
- **Số viết bằng CHỮ SỐ trong caption**: "ba mươi giây" → "30 giây", "Bước một" → "Bước 1", giữ nguyên đơn vị. Tự động bởi `caption_display()`. Giọng đọc vẫn đọc tự nhiên (Google TTS expand chữ số).
- Chính tả chuẩn (vd "Đừng" ≠ "Dừng") — soát kỹ vì lỗi dính vào CẢ caption lẫn giọng đọc.
- Giọng vi-VN rotate nam/nữ theo ngày (đã có).
- BGM tech/electronic/upbeat (pool sôi động, loại track chậm) — `volumex 0.16`. Drop file `audio/bgm_18+.mp3` là tự dùng.

## 5. ĐĂNG & ĐO

- Đăng đều mỗi ngày (1 video/24h) — consistency > volume bùng nổ.
- Sau 24h xem "Viewed vs Swiped Away" trong Studio: tụt mạnh ở giây 3 = hook fail; tụt từ từ = content drift.
- Mục tiêu retention ≥ 73% (viral > 75%), completion peak ở 50-60s.

---

## Nguồn nghiên cứu
- virvid.ai — first-3-seconds hook & faceless retention 2026
- opus.pro — Shorts hook formulas
- inbeat.co, capcut.com — viral structure & pacing
- vidIQ explore-and-exploit (qua tổng hợp) — retention > raw views

**END** — cập nhật khi học thêm pattern mới.
