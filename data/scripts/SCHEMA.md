# Script JSON Schema — Tài Chính 5 Phút

> **Cập nhật 29/05/2026** — Tích hợp findings từ research top 22 viral finance Shorts VN (6 tháng gần đây).
> Insight chính: comedy/skit + show-off tiết kiệm dominate (avg 1M-3M views); pure education chỉ đạt 10-30k views.
> User KHÔNG thể format comedy face-camera → chiến lược: **HYBRID character-driven story + practical demo**.

Mỗi file `data/scripts/{idea_id}.json` phải đúng format dưới đây để pipeline assemble video chạy được.

## Niche reality check (từ research API)

| Content type | Avg views/video | Ceiling |
|---|---|---|
| Comedy skit về tiết kiệm | **1,294,344** | 3.3M (face-camera, out of scope với pipeline AI voice) |
| Show-off khoản tiết kiệm năm | 408,646 | 947k (character-driven, AI voice OK) |
| Practical tip + visual demo | 340,532 | 340k (excel template, mẹo điện) |
| Education pure (lý thuyết) | 10,669 | 10-30k (current user format) |
| Tâm lý + cảnh báo cross-over | 558,833 | 558k (storytelling-friendly) |

**Hàm ý:** Format cũ "Vì sao 99% người Việt làm sai" → ceiling 10-30k views. Muốn break 100k → cần **character story + result reveal + practical demo**.

## Schema chuẩn

```json
{
  "title": "string, 50-80 ký tự, TIẾNG VIỆT CÓ DẤU, có 3-5 hashtag bundle cuối",
  "description": "string, 200-300 từ, line 1 là hook trong 100 chars, 3 link affiliate placeholder [LINK_INFINA] [LINK_VPS] [LINK_TPBANK], CTA subscribe, 8-10 hashtag finance VN",
  "tags": ["string array, 12-20 tag, mix VN có dấu + English, có brand tag + topic tag + viral tag"],
  "scenes": [
    {"voiceover": "VN có dấu, 1-2 câu ngắn", "visual_keyword": "english only, 3-5 từ specific với vietnamese context"},
    ...8 phần tử
  ]
}
```

## Quy tắc bắt buộc

### Title

- **Length: 50-80 ký tự** (tăng từ <60 — viral Shorts avg 67 chars)
- Phải có số cụ thể (90%, 5 triệu, 1 năm, 15tr...) → tăng CTR
- **Hashtag bundle 3-5** cuối title: `#shorts #taichinh #tietkiem #trending` (top performers dùng 3-7 hashtag)
- 1 emoji optional boost CTR: 🔥 ❤️ 😅 (chọn 1 phù hợp tone)
- VN có dấu đầy đủ: à á ả ã ạ ă ắ ằ ẳ ẵ ặ â ấ ầ ẩ ẫ ậ đ è é ẻ ẽ ẹ ê ế ề ể ễ ệ ì í ỉ ĩ ị ò ó ỏ õ ọ ô ố ồ ổ ỗ ộ ơ ớ ờ ở ỡ ợ ù ú ủ ũ ụ ư ứ ừ ử ữ ự ỳ ý ỷ ỹ ỵ

### Title Formula (8 mẫu — PHÂN BỔ ƯU TIÊN theo viral data)

**🥇 PRIORITY HIGH — Formula F/G/H (character + reveal + tâm lý) — dùng 60% scripts:**

**Formula F — Story character + result reveal** (top viral pattern, avg 400k-1M views):
- `Anh Tuấn Lương 15Tr Tiết Kiệm 1 Năm Được Bao Nhiêu? #shorts #tietkiem #taichinh`
- `Chị Lan 28 Tuổi Áp Dụng 50/30/20 — Sau 6 Tháng Có Gì? 🔥 #shorts #tietkiem`
- `Cô Hoa Công Nhân Lương 8Tr Vẫn Mua Được Nhà — Cách Nào? #shorts #tietkiem`

**Formula G — Show-off khoản tiết kiệm/result** (avg 400-900k views):
- `Khoản Tiết Kiệm 1 Năm Của Dân VP Lương 18Tr ❤️ #shorts #tietkiem #shortvideo`
- `Sau 30 Ngày Track Chi Tiêu Bằng App — Đây Là Số Tiền Tôi Có #shorts #taichinh`
- `Thành Quả 12 Tháng Đầu Tư Quỹ Mở 500K/Tháng 📈 #shorts #dautu`

**Formula H — Bẫy tâm lý/cảnh báo** (avg 500k+ views, viral cross-over):
- `5 Bẫy Tâm Lý Khiến Bạn Mất Tiền Mỗi Tháng 😅 #shorts #tietkiem #tamlytien`
- `Black Friday Là Cú Lừa Tâm Lý — 99% Mắc Bẫy #shorts #taichinh #canhbao`
- `App Vay Tiêu Dùng Bẫy Lãi 100%/Năm — Cách Nhận Biết 🔥 #shorts #canhbao`

**🥈 PRIORITY MEDIUM — Formula A/B/C/D (educational, ceiling 30k views) — dùng 30% scripts:**

**Formula A — Vì Sao + %** (validated — user video đạt 1k views):
- `Vì Sao 99% Người Việt Làm Sai Quy Tắc 50/30/20? #shorts #taichinh #tietkiem`
- `Vì Sao Buffett Mua Coca-Cola 36 Năm Không Bán? #shorts #dautu`

**Formula B — Cách + con số + outcome:**
- `Cách Tiết Kiệm 2 Triệu/Tháng Không Cần Nỗ Lực #shorts #tietkiem #taichinh`
- `Cách Dùng AI Lên Budget Gia Đình Trong 5 Phút #shorts #aitaichinh`

**Formula C — [Con số] + sai lầm/dấu hiệu:**
- `5 Sai Lầm Tiền Tuổi 30 Sẽ Hối Hận Đời 🔥 #shorts #tamlytien #taichinh`
- `5 Dấu Hiệu Bạn Đang Sống Dưới Khả Năng #shorts #tietkiem`

**Formula D — Bí mật + topic:**
- `Lãi Kép: Kỳ Quan Thứ 8 Einstein Cảnh Báo #shorts #dautu`
- `Bí Mật Quỹ Mở Mà Ngân Hàng Không Nói Bạn #shorts #dautu #quymo`

**🥉 PRIORITY LOW — Formula E (practical demo) — dùng 10% scripts:**

**Formula E — Mẹo cụ thể + tool + time:**
- `Excel Template Track 100 Khoản Chi 1 Tháng — File Miễn Phí 📊 #shorts #taichinh`
- `Mẹo Tiết Kiệm Tiền Điện 30%/Tháng Không Cần Thay Đồ #shorts #tietkiem`

**Quy tắc capitalization (thống nhất brand):**
- Dùng **Title Case** (mỗi từ chính viết hoa chữ đầu)
- Giữ nguyên dấu Việt: `Vì`, `Mãi Mãi`, `Người Việt`...
- KHÔNG ALL CAPS (trừ con số hoặc emphasis 1 từ)
- Liên từ/giới từ ngắn giữ thường: `của`, `cho`, `và`, `để`, `trong`, `với`
- Hashtag viết liền không khoảng trắng, lowercase

### Scenes (8 cảnh, tổng 45-55s)

**1. HOOK (3s, 8-12 từ) — VISUAL + CHARACTER PRIORITY:**

❌ TỆ (current format — ceiling 10-30k views):
- "Bạn có biết 99% người Việt làm sai quy tắc 50/30/20 không?"
- "Cách tiết kiệm 2 triệu/tháng — bí quyết đây."

✅ TỐT (viral pattern — ceiling 100k-1M views):
- **Character intro:** "Anh Tuấn, 32 tuổi, lương 15 triệu — sau 1 năm anh có 54 triệu trong tài khoản tiết kiệm."
- **Result reveal:** "Sau 6 tháng áp dụng 50/30/20, đây là số tiền tôi có — và 1 sai lầm tôi đã mắc."
- **Shock number:** "30 triệu trong 12 tháng với lương 15 triệu — không phải đùa."
- **Cảnh báo tâm lý:** "Black Friday vừa rồi — bạn vừa rơi vào bẫy tâm lý 99% người mắc."

**2. PAIN/SETUP (5-7s):** Nỗi đau cụ thể + relatable cho dân VP Việt
- Lương 15-20tr không đủ, cuối tháng hết tiền, không biết tiền đi đâu
- Vợ chồng cãi nhau vì chi tiêu, sinh con không dám tiêu, không có quỹ khẩn cấp
- Đầu tư mất tiền vì FOMO, app vay tiêu dùng nợ chồng nợ

**3-6. CỐT LÕI (30-35s):** Step-by-step storytelling
- **Mỗi scene 1 bước CỤ THỂ** + số liệu thực tế
- Tránh lý thuyết trừu tượng — luôn quay về câu chuyện character (Anh Tuấn làm gì tháng 1, tháng 3, tháng 6)
- Scene 5 hoặc 6 BẮT BUỘC: số tiền specific: "tháng đầu anh tiết kiệm 3tr, tháng 6 lên 5tr, sau 1 năm tổng 54tr"
- Nếu Formula F/G (character) → scene 3-6 là journey timeline với numbers
- Nếu Formula H (cảnh báo) → scene 3-6 là 3-5 bẫy cụ thể + cách tránh

**7. CTA/PATTERN INTERRUPT (3-4s):**
- Câu hỏi mở để force comment, vd:
  - "Bạn đã từng áp dụng 50/30/20 chưa? Comment kết quả của bạn, mình đọc hết."
  - "Bạn có nhận ra bẫy nào ở trên? Comment số bẫy bạn mắc, mình tư vấn."
  - "Lương của bạn bao nhiêu? Comment, mình tính cho bạn budget chuẩn."

**8. SUBSCRIBE + DISCLAIMER (3-4s):**
- **Value prop subscribe** tailored theo topic (KHÔNG generic "theo dõi để học mẹo tiền")
- **Disclaimer YMYL ngắn:** "Đây là góc nhìn cá nhân, không phải lời khuyên tài chính."

**Outro pattern chuẩn (Formula winning):**
```
"Subscribe [value prop cụ thể theo topic] — kênh đăng mỗi 6h sáng. 
Đây là góc nhìn cá nhân, không phải lời khuyên tài chính."
```

Ví dụ value prop tailored theo pillar:
- **saving:** "Subscribe để có lần đầu cuối tháng còn dư tiền..."
- **investing:** "Subscribe để hết nói 'giá như tôi đầu tư sớm'..."
- **psychology:** "Subscribe để hiểu vì sao người giàu nghĩ khác..."
- **ai-finance:** "Subscribe nếu bạn cũng muốn AI quản chi tiêu thay mình..."

### Voiceover

- Mỗi scene 1-2 câu ngắn
- Dùng dấu chấm/phẩy đúng → TTS đọc có ngắt nghỉ tự nhiên
- KHÔNG viết "[disclaimer]" — viết tự nhiên trong scene 8
- Nói như bạn bè 28 tuổi nói với nhau, KHÔNG academic
- **Character voice consistency:** Nếu hook giới thiệu "Anh Tuấn" → toàn script gọi "Anh Tuấn", không đổi sang "anh ấy" trừ khi cần variation

### Visual keyword (TIẾNG ANH)

- 3-5 từ specific với **vietnamese/asian context** (boost relevance)
- 8 scene phải KHÁC nhau hoàn toàn (mix wide + close-up + abstract)

**❌ TỆ (generic):**
- "money"
- "business"
- "finance chart"

**✅ TỐT (character + context):**
- "vietnamese office worker counting money desk"
- "young asian woman thinking budget excel laptop"
- "vietnamese family budget discussion kitchen"
- "hand writing financial goals notebook close-up"
- "asian person stressed bills paper morning"
- "vietnamese piggy bank coins falling slow motion"
- "excel spreadsheet budget colorful pie chart"

**Pattern visual cho Formula F (character story):**
- Scene 1: character wide shot — "vietnamese young man office stressed"
- Scene 2: pain visual — "calculator empty wallet kitchen night"
- Scene 3-6: journey timeline — "calendar pages flipping", "money jar growing weeks", "excel budget tracker screen"
- Scene 7: question close-up — "person looking camera thinking"
- Scene 8: subscribe button graphic — "youtube subscribe red button animated"

### Description (NEW rules)

- **Line 1: HOOK 80-100 chars** — YouTube cắt ở 100 char trên feed, đây là phần quan trọng nhất
- Lines 2-3: Story expand
- Mid: 3 affiliate placeholder `[LINK_INFINA]` `[LINK_VPS]` `[LINK_TPBANK]`
- CTA Subscribe
- **Hashtag bundle 8-12** (mix #shorts #taichinh #tietkiem #dautu #vanphongtudong)

**Mẫu description:**
```
Anh Tuấn 32 tuổi, lương 15 triệu — sau 1 năm tiết kiệm được 54 triệu. Đây là cách 🔥

Anh không phải dùng app trade chứng khoán nào, không vay nợ. Chỉ áp dụng quy tắc 50/30/20 + 3 thói quen nhỏ mỗi sáng. Bạn cũng có thể làm được — bắt đầu từ tháng này.

📚 Tài liệu chi tiết:
→ Đầu tư quỹ mở từ 100k: [LINK_INFINA]
→ Mở tài khoản tiết kiệm online: [LINK_TPBANK]
→ Vay tiêu dùng lãi suất ưu đãi: [LINK_VPS]

🔔 Subscribe @taichinh5phut.official để mỗi sáng 6h có 1 mẹo tiền cho dân VP Việt.

⚠️ Đây là góc nhìn cá nhân, không phải lời khuyên tài chính.

#shorts #taichinh #tietkiem #dautu #50_30_20 #dan_van_phong #luong15trieu #tienbac #tietkiemtien #shortvideo
```

### Tags (NEW rules)

- **12-20 tags** (tăng từ 8-15) — top viral có 18-40 tags
- 3 nhóm:
  - **Brand tag (3-4):** "tài chính 5 phút", "taichinh5phut", "@taichinh5phut.official"
  - **Topic tag (6-10):** specific theo nội dung — "tiết kiệm tiền lương 15 triệu", "quỹ mở việt nam 2026"...
  - **Viral tag (3-5):** "shorts", "shortvideo", "trending", "viralshorts", "tips"

### YMYL Compliance

- KHÔNG khuyến nghị mã cổ phiếu cụ thể (vd: "mua HPG", "mua VIC")
- KHÔNG hứa hẹn ROI cụ thể ("chắc chắn lời 20%")
- KHÔNG cliff fictional character làm như thật — nếu dùng "Anh Tuấn 32 tuổi" cần add: "Đây là ví dụ minh họa, kết quả mỗi người khác nhau"
- Scene 8 PHẢI có disclaimer
- Pipeline sẽ tự append disclaimer dài vào description khi upload

### Anti-templating (BẮT BUỘC khi gen batch)

- Mỗi 5 script consecutive PHẢI mix 3+ Formula khác nhau (vd: 2 character F + 1 result G + 1 cảnh báo H + 1 educational A)
- Character name rotation: Tuấn, Lan, Hùng, Hoa, Minh, Trang... (không lặp "Anh Tuấn" 30 scripts)
- Lương number variation: 8tr, 12tr, 15tr, 18tr, 22tr, 28tr, 35tr — không stuck "lương 15 triệu" mọi script
- Timeline variation: 1 tháng, 3 tháng, 6 tháng, 1 năm, 2 năm — không stuck "1 năm" mọi script
- Tone rotation: 30% storytelling cảm xúc, 30% urgency cảnh báo, 20% nghiêm túc educational, 20% triết lý

## File mẫu

Xem `data/scripts/5kAtn4cBJPI` (Quy Tắc 50/30/20 — 1027 views) — đây là proof of concept tốt nhất hiện có với format cũ. Format mới (F/G/H) chưa có sample, sẽ tạo khi gen idea 13.
