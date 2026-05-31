# Script JSON Schema — Tài Chính 5 Phút

> **Cập nhật 31/05/2026** — Tích hợp full rules từ iteration 1-7 với user feedback.
> Kênh: "Tài Chính 5 Phút" `@taichinh5phut.official`
> Pillar: Tài chính cá nhân + AI tools cho dân văn phòng Việt Nam (low YMYL).

---

## 1. SCHEMA chuẩn JSON

```json
{
  "idea_id": <int>,
  "title": "<50-80 ký tự, Title Case VN có dấu, kết bằng 3-5 hashtag bundle, optional 1 emoji>",
  "hook": "<câu hook punchy 30-60 ký tự, hiển thị visual 2.5s đầu, mô tả character/result reveal/shock>",
  "description": "<200-300 từ, LINE 1 là hook 80-100 chars + story + 3 link [LINK_INFINA][LINK_VPS][LINK_TPBANK] + CTA + 8-12 hashtag>",
  "tags": ["<12-20 tag mix brand + topic + viral>"],
  "scenes": [
    {"voiceover": "<VN có dấu, 1-2 câu ngắn, KHÔNG viết tắt>", "visual_keyword": "<english 3-5 từ với vietnamese/asian context>"},
    ...8 phần tử
  ]
}
```

---

## 2. QUY TẮC NỘI DUNG (đã chốt với user)

### 2.1 KHÔNG VIẾT TẮT — bắt buộc 100%

| Viết tắt | Phải viết đầy đủ |
|---|---|
| VN | Việt Nam |
| HN | Hà Nội |
| SG | Sài Gòn |
| HCM / TPHCM | Hồ Chí Minh / Thành phố Hồ Chí Minh |
| VP | văn phòng |
| Tr / tr | Triệu / triệu |
| K / k (sau số) | nghìn |
| TK | tài khoản |
| CK | chứng khoán |
| HR | nhân sự |
| CCCD | căn cước công dân |
| BNPL | trả góp 0% lãi suất |
| VND (currency context) | đồng (hoặc "đồng Việt Nam") |

**Giữ nguyên** (globally accepted trong tiếng Việt):
- AI, IT, KPI, ATM, Excel, ChatGPT, Notion, Gemini
- Brand names: SSI, VPS, VnDirect, TPBank, Infina, Cake...

### 2.1d AI IMAGE FALLBACK (cho scene Pexels không match)

User feedback iter 12: "Nếu không đủ video trên Pexels thì gen ảnh AI"

**Pipeline auto-fallback (default):**
- Try Pexels stock first (dedup via exclude_ids)
- Nếu Pexels FAIL (rate limit, no results, all duplicates) → AI image gen
- AI provider: **Pollinations Flux** (free, no API key, public Stable Diffusion)
- Convert AI image → vertical video (1080×1920) với Ken Burns effect (slow zoom + pan) via FFmpeg

**Script optional fields (per scene):**
- `"visual_style": "auto"` (default) — Pexels first, fallback AI
- `"visual_style": "ai"` — luôn dùng AI, skip Pexels
- `"visual_style": "stock"` — chỉ Pexels (legacy mode)
- `"visual_prompt": "<detailed prompt>"` — override prompt cho AI (nếu thiếu dùng `visual_keyword`)

**Khi nào dùng `visual_style: "ai"`:**
- Concept đặc thù VN không có trên Pexels (gửi tiết kiệm online, app ngân hàng số VN)
- Cần consistency character (Anh Tuấn 32 tuổi, Chị Mai marketing)
- Visual concept abstract (lãi kép, compound effect)

**Khi nào dùng `visual_style: "stock"`:**
- Concept universal (money close-up, calculator, office worker)
- Pexels có nhiều options

### 2.1c KHÔNG LẶP CLIP PEXELS TRONG VIDEO

User feedback iter 10: "Có những đoạn video bị lặp lại, bỏ nó và thay bằng video khác."

**Pipeline rule (already implemented):**
- `fetch_all_clips` chạy SEQUENTIAL (không concurrent) để share `used_ids` set
- `download_pexels_clip(keyword, output_path, exclude_ids)` track Pexels video_id đã dùng
- `per_page=15` (was 5) → nhiều lựa chọn hơn, tỷ lệ trùng thấp
- 8 clips trong 1 video bắt buộc 8 video_id KHÁC NHAU

**Script writer rule (cho người gen script):**
- `visual_keyword` mỗi scene PHẢI khác nhau hoàn toàn về concept
- Tránh stacking keywords gần nhau (vd: "vietnamese phone banking" + "vietnamese phone open account" → Pexels có thể trả về cùng clip)
- Mix wide shot + close-up + abstract:
  - Wide: "vietnamese family kitchen home"
  - Close-up: "hand counting money close-up"
  - Abstract: "calendar pages flipping months"
- 8 scenes nên có 3+ themes khác nhau (subject + setting + action)

### 2.1a KHÔNG CONTENT ĐẦU TƯ TÀI CHÍNH

User không muốn content về **đầu tư** (chốt 31/05 iteration 9). Bỏ:
- Chứng khoán (DCA, cổ phiếu, broker, mở tài khoản chứng khoán)
- Quỹ mở (mutual funds, đầu tư quỹ)
- Đầu tư vàng (vàng SJC, vàng miếng)
- Lãi kép Einstein dài hạn
- Buffett wisdom đầu tư

**Giữ:** Saving (tiết kiệm chi tiêu), gửi tiết kiệm online (saving instrument không phải investing), mua nhà / xe / quỹ khẩn cấp (goal-based saving), psychology, AI tools cho budget cá nhân.

**3 pillar còn lại:** saving (50%) + psychology (35%) + ai-finance (15%).

### 2.1bis KHÔNG QUẢNG CÁO APP/BRAND CỤ THỂ

**Tuyệt đối không nhắc tên app/dịch vụ cụ thể.** Dùng generic terms:

| Brand/App cụ thể | Generic term |
|---|---|
| TPBank, Cake, Timo, VietCapital | "app ngân hàng số" / "ngân hàng số" |
| Money Lover, Spendee | "app quản lý chi tiêu" |
| Infina | "ứng dụng đầu tư quỹ mở" |
| SSI, VPS, VND, VnDirect | "công ty chứng khoán" |
| VFM, Dragon Capital | "công ty quản lý quỹ" |
| ChatGPT, Claude, Gemini, Notion AI | "AI trợ lý" |
| Notion | "app note" |

**Description footer KHÔNG có** `[LINK_INFINA]` `[LINK_TPBANK]` `[LINK_VPS]` placeholders nữa. Pipeline auto-append chỉ disclaimer + Kevin MacLeod credit + email contact.

**Giữ nguyên:** AI (generic term), Excel/Google Sheets (generic productivity), Shopee/Lazada (chỉ trong context cảnh báo tâm lý).

### 2.2 KHÔNG ký tự `<` `>` trong description/title/voiceover

YouTube API reject 400 invalidDescription nếu có `<` hoặc `>`.
- ❌ "chi >50k" — REJECT
- ✅ "chi trên 50 nghìn" — OK

Pipeline tự sanitize `<` → `‹` và `>` → `›` defense-in-depth.

### 2.3 Hook field bắt buộc + MUST MATCH scene 1 voice start (iter 14)

**CRITICAL RULE:** `hook` field PHẢI xuất hiện VERBATIM ở đầu `scenes[0].voiceover`.

Lý do: pipeline có logic skip caption chunks trùng hook visual để tránh duplicate hiển thị. Nếu hook ≠ scene 1 start, skip không kích hoạt → hook visual + caption đầu hiện 2 nội dung khác nhau = cảm giác **lặp đầu video**.

❌ TỆ (hook ≠ scene 1 start):
```json
{
  "hook": "Anh Tuấn tiết kiệm 54 triệu trong 1 năm!",
  "scenes": [{"voiceover": "Anh Tuấn 32 tuổi, kế toán Hà Nội, lương 15 triệu. Sau 1 năm anh có 54 triệu..."}]
}
```
→ Hook visual + caption "Anh Tuấn 32 tuổi" cùng hiện 0-2.5s = lặp khác nội dung.

✅ TỐT (hook = scene 1 start):
```json
{
  "hook": "Anh Tuấn lương 15 triệu tiết kiệm 54 triệu trong 1 năm!",
  "scenes": [{"voiceover": "Anh Tuấn lương 15 triệu tiết kiệm 54 triệu trong 1 năm! Anh là kế toán Hà Nội, trước đó 3 năm không nổi 5 triệu cuối tháng."}]
}
```
→ Skip logic kích hoạt, caption chỉ hiện phần sau hook.

Mỗi script có `"hook"` explicit (KHÔNG dựa fallback auto-extract):
- **Độ dài:** 30-60 ký tự (1 câu ngắn punchy)
- **Style:** character intro + outcome / shock number / cảnh báo
- **Vai trò:** Hiển thị visual 2.5s đầu video — bí quyết "stop scroll"

**Ví dụ tốt:**
- "Anh Tuấn lương 15 triệu tiết kiệm 54 triệu trong 1 năm!"
- "Bạn mất 5 triệu mỗi tháng vì 5 bẫy tâm lý này!"
- "Sau 30 ngày track chi tiêu — đây là số tiền tôi tiết kiệm"

**Ví dụ TỆ:**
- "Vì sao 99% người Việt làm sai 50/30/20? Hãy cùng tôi tìm hiểu trong video này." (quá dài)
- "Quỹ mở là gì?" (quá ngắn, không hook)

### 2.4 Scene 1 voiceover: hook + context

Scene 1 = hook punchy (overlap với `hook` field) + 1-2 câu context. Pipeline sẽ SKIP caption chunks trùng hook visual (tránh duplicate hiển thị).

### 2.5 Title Formula priority

| Priority | Formula | Pattern | Target views |
|---|---|---|---|
| 🥇 HIGH | F (character story) | "[Tên Tuổi] Lương [X] Triệu — [Outcome]" | 400k-1M |
| 🥇 HIGH | G (result reveal) | "Sau [time] [action] — [reveal số liệu]" | 400k-900k |
| 🥇 HIGH | H (tâm lý/cảnh báo) | "[N] Bẫy / Cú Lừa + [outcome]" | 500k+ |
| 🥈 MED | A (Vì Sao + %) | "Vì Sao 99% [target] [problem]?" | 10-30k |
| 🥈 MED | B (Cách + outcome) | "Cách [action] [outcome]" | 10-30k |
| 🥈 MED | C (Số + sai lầm) | "[N] Sai Lầm / Dấu Hiệu [topic]" | 10-30k |
| 🥈 MED | D (Bí mật + topic) | "Bí Mật / Cảnh Báo [topic]" | 10-30k |
| 🥉 LOW | E (practical demo) | "[Tool] + outcome + [time]" | 50-300k |

**Phân bổ 30 scripts:** 60% F/G/H + 30% A-D + 10% E.

### 2.6 Cấu trúc 8 scenes (45-55s tổng)

1. **HOOK** (3s): Câu hook punchy (giống `hook` field)
2. **PAIN / SETUP** (5-7s): Nỗi đau cụ thể của dân văn phòng Việt Nam
3-6. **CỐT LÕI** (30-35s): Storytelling timeline với character + số liệu cụ thể
   - Scene 5 hoặc 6 BẮT BUỘC: "Tôi tự áp dụng cách này X tháng và thấy..."
7. **CTA / PATTERN INTERRUPT** (3-4s): Câu hỏi force comment
8. **SUBSCRIBE + DISCLAIMER** (3-4s):
   - Value prop subscribe tailored theo pillar
   - YMYL disclaimer: "Đây là góc nhìn cá nhân, không phải lời khuyên tài chính."

### 2.7 Visual keyword (TIẾNG ANH)

- 3-5 từ specific với **vietnamese/asian context**
- 8 scene phải KHÁC nhau hoàn toàn

❌ Generic: "money", "business", "finance chart"
✅ Specific: "vietnamese office worker counting money desk", "young asian woman thinking budget excel laptop"

---

## 3. QUY TẮC VISUAL (Pipeline rules đã chốt)

### 3.1 Caption (sub karaoke)

| Element | Value | Lý do |
|---|---|---|
| **Font** | BeVietnamPro-ExtraBold (weight 800) | Vietnamese-optimized + balanced bold |
| **Fontsize** | 110 | Đủ to dễ đọc mobile |
| **Color fill** | white | Clean readable |
| **Stroke** | black, width 3 | Mỏng để fill không bị che |
| **Shadow** | TextClip đen offset y+7px behind | Tạo 3D bold look |
| **BG box** | KHÔNG | Cleaner look |
| **Position** | y=1280 (middle-lower) | Tránh che YouTube UI dưới |
| **Width** | 980 | |
| **Chunks** | max_words=3 | Nhỏ → chuyển nhanh khớp voice |
| **Lead time** | 0.25s trước voice | Compensate TTS ramp-up |
| **Timing** | word-count proportion | Tiếng Việt monosyllabic ≈ word ≈ syllable ≈ TTS time |
| **Scene 1 skip** | Skip chunks trùng hook content | Tránh duplicate |

### 3.2 Hook visual (đầu video)

| Element | Value | Lý do |
|---|---|---|
| **Font** | Montserrat-ExtraBold | Hook rộng hơn caption, Latin OK |
| **Color** | white | Yellow + thick stroke bị render đen ám trên IM7 |
| **Stroke** | black, width 4 | |
| **BG box** | rgba(0,0,0,0.65) semi-black pill | Distinctive khỏi caption |
| **Position** | y=700 (upper area) | Tránh che subject + YouTube UI |
| **Duration** | 2.5s | Đủ time đọc |
| **Fontsize** | Dynamic 82-125 theo độ dài hook | Hook ngắn → font lớn |
| **Fade** | fadein 0.2s + fadeout 0.4s | Smooth |

### 3.3 Disclaimer (đầu video)

- Position y=100 (top strip)
- fontsize 38, color white, bg_color="rgba(0,0,0,0.7)"
- Duration 0-4s
- Text: "Video chỉ mang tính giáo dục, KHÔNG phải lời khuyên đầu tư. Hãy tham khảo chuyên gia tài chính."

---

## 4. QUY TẮC PIPELINE / ENCODER

### 4.1 Encoder

| Platform | Codec | Threads | Preset | FPS | Bitrate |
|---|---|---|---|---|---|
| Windows local | libx264 | 8 | ultrafast | 24 | 5500k (prod), 3500k (--fast) |
| Linux CI | libx264 | 4 | veryfast | 24 | 5500k |
| macOS | libx264 | 4 | medium | 24 | 5500k |

**Note:** h264_amf (AMD GPU) test fail với MoviePy 1.0.3 — preset arg không tương thích. Stick libx264.

### 4.2 Render output

- Resolution: 1080x1920 (1080p vertical Shorts)
- Codec: H.264 main/high profile
- Audio: AAC 192kbps
- Faststart for streaming

### 4.3 Upload privacy

- Default: **private** (env var `YT_PRIVACY` override default)
- Workflow CI: set `YT_PRIVACY=public` khi sẵn sàng phát hành chính thức
- Local manual: privacy=private để review

### 4.4 Sanitization layers

Pipeline tự strip `<` `>` ở 2 lớp:
1. Title: `safe_title = script_data["title"][:100].replace("<", "‹").replace(">", "›")`
2. Description: tương tự
3. Trong scripts: batch clean qua regex (đã apply)

---

## 5. QUY TẮC ANTI-TEMPLATING

Khi gen batch script:
- **Character rotation 10 names:** Tuấn, Lan, Hùng, Hoa, Minh, Trang, Quân, Linh, Thảo, Nam, Hà
- **Lương rotation:** 8tr, 12tr, 15tr, 18tr, 22tr, 28tr, 35tr
- **Timeline:** 1 tháng, 3 tháng, 6 tháng, 1 năm, 2 năm, 5 năm
- **Tone rotation:** 30% storytelling cảm xúc, 30% urgency cảnh báo, 20% nghiêm túc, 20% triết lý
- Mỗi 5 script consecutive PHẢI mix 3+ Formula khác nhau

---

## 6. YMYL Compliance

- KHÔNG khuyến nghị mã cổ phiếu cụ thể (vd: "mua HPG", "mua VIC")
- KHÔNG hứa hẹn ROI cụ thể ("chắc chắn lời 20%")
- KHÔNG nhắc tên app vay tiền/lừa đảo (cảnh báo OK, nhưng disclaim)
- Scene 8 PHẢI có disclaimer "Đây là góc nhìn cá nhân, không phải lời khuyên tài chính"
- Pipeline auto-append disclaimer dài vào description: "Đây là góc nhìn cá nhân, KHÔNG phải lời khuyên đầu tư hay tài chính..."

---

## 7. Description format

```
<Hook line 80-100 chars> emoji optional

<Body 100-150 từ — story expand, character context, value teaser>

🔗 Tài liệu tham khảo:
→ Đầu tư quỹ mở từ 100 nghìn: [LINK_INFINA]
→ Mở tài khoản tiết kiệm online: [LINK_TPBANK]
→ Mở tài khoản chứng khoán: [LINK_VPS]

🔔 Subscribe @taichinh5phut.official — mỗi sáng 6 giờ 1 mẹo tiền cho dân văn phòng Việt.

⚠️ Đây là góc nhìn cá nhân, không phải lời khuyên tài chính. Kết quả mỗi người khác nhau.

#shorts #taichinh #tietkiem #danvanphong + 4-8 hashtag specific
```

---

## 8. File mẫu tham khảo

- **Idea 13 (Anh Tuấn lương 15 triệu):** Formula F character story chuẩn
- **Idea 15 (Chị Hà 5 bẫy tâm lý):** Formula H cảnh báo + character intro
- **Idea 16 (50/30/20 sai):** Formula A educational với auto-hook

---

**END OF SCHEMA** — Cập nhật mỗi khi có rule mới chốt với user.
