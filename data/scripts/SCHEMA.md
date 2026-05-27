# Script JSON Schema — Văn Phòng Tự Động

> **PIVOT 27/05/2026:** Project đổi niche từ "Tài Chính 5 Phút" (YMYL finance) → **"Văn Phòng Tự Động"** (AI Automation cho dân VP Việt). Pipeline + code giữ 100%, chỉ đổi content + branding.

Mỗi file `data/scripts/{idea_id}.json` phải đúng format dưới đây để pipeline assemble video chạy được.

## Niche & Audience mới

- **Niche chính:** AI Tự Động Hoá Cho Dân Văn Phòng VN (automation, ChatGPT/Claude, Notion, Excel+AI)
- **Audience:** Nhân viên VP 25-40 tuổi, lương 10-30tr, muốn tiết kiệm 50% thời gian bằng AI
- **4 Pillar:**
  1. 🤖 **ai-tools** (40%) — ChatGPT/Claude/Gemini, prompts, custom GPTs
  2. ⚡ **automation** (35%) — n8n, Make.com, Zapier, workflows
  3. 📊 **excel-ai** (15%) — Excel/Sheets + AI plugins, formulas
  4. 📝 **notion-productivity** (10%) — Notion AI, GTD, templates
- **KHÔNG còn YMYL** — không khuyến nghị đầu tư/thuốc/y tế. Vẫn cần disclaimer nhẹ "kết quả mỗi người khác nhau"

## Schema chuẩn

```json
{
  "title": "string, <= 60 ký tự, TIẾNG VIỆT CÓ DẤU, kết thúc bằng #shorts",
  "description": "string, 200-300 từ TIẾNG VIỆT CÓ DẤU, gồm: hook 2 câu + 3 link affiliate placeholder [LINK_INFINA] [LINK_VPS] [LINK_TPBANK] + CTA subscribe + 5 hashtag",
  "tags": ["string array, 8-15 tag, mix VN có dấu + English, max 30"],
  "scenes": [
    {"voiceover": "VN có dấu, 1-2 câu ngắn", "visual_keyword": "english only, 2-4 từ cụ thể"},
    ...8 phần tử
  ]
}
```

## Quy tắc bắt buộc

### Title
- Tối đa 60 ký tự (YouTube cut ở 100, nhưng <60 hiển thị đẹp nhất trên mobile)
- Phải có số cụ thể (90%, 5 triệu, 2 phút...) → tăng CTR
- Kết thúc bằng `#shorts`
- VN có dấu đầy đủ: à á ả ã ạ ă ắ ằ ẳ ẵ ặ â ấ ầ ẩ ẫ ậ đ è é ẻ ẽ ẹ ê ế ề ể ễ ệ ì í ỉ ĩ ị ò ó ỏ õ ọ ô ố ồ ổ ỗ ộ ơ ớ ờ ở ỡ ợ ù ú ủ ũ ụ ư ứ ừ ử ữ ự ỳ ý ỷ ỹ ỵ

### Title Formula (4 mẫu winning — phân bổ đều, KHÔNG dùng 1 formula liên tục)

**Formula A — Cách + con số + outcome** (work tốt cho automation):
- `Cách Tự Động Hoá Email Công Việc Trong 5 Phút Với n8n #shorts`
- `Cách ChatGPT Viết JD Tuyển Dụng 30 Giây #shorts`

**Formula B — Vs/So sánh + chọn lựa:**
- `Make.com vs n8n vs Zapier — Chọn Cái Nào Cho Dân VP Việt? #shorts`
- `Notion AI vs ChatGPT — Dùng Cái Nào Cho Công Việc? #shorts`

**Formula C — [Con số] + lợi ích cụ thể:**
- `5 Custom GPT Trợ Lý Cho Dân VP Việt — Setup Miễn Phí #shorts`
- `5 Prompt ChatGPT Cứu Tinh Dân VP Trước Deadline #shorts`

**Formula D — [Tool] Là Gì + benefit:**
- `n8n Là Gì — Tự Động Hoá Công Việc Miễn Phí Trong 5 Phút #shorts`
- `Cursor AI Là Gì — IDE Cho Dân Không Phải Dev Việt #shorts`

**Formula E — AI [Verb] [Object] trong [time]:**
- `AI Tóm Tắt Cuộc Họp Zoom 1 Tiếng → 5 Phút Đọc #shorts`
- `AI Làm Slide PowerPoint Từ Outline Trong 1 Phút #shorts`

**Quy tắc capitalization (thống nhất brand):**
- Dùng **Title Case** (mỗi từ chính viết hoa chữ đầu)
- Giữ nguyên dấu Việt: `Vì`, `Mãi Mãi`, `Người Việt`...
- KHÔNG ALL CAPS (trừ con số hoặc emphasis 1 từ)
- Liên từ/giới từ ngắn giữ thường: `của`, `cho`, `và`, `để`, `trong`, `với`

### Scenes (8 cảnh, tổng 45-55s)
1. **HOOK** (3s, 8-12 từ): Câu hỏi shock hoặc demo result đáng kinh ngạc có con số (vd: "AI làm 3 tiếng việc của bạn trong 30 giây")
2. **PAIN POINT** (5-7s): Nỗi đau cụ thể của dân VP Việt — copy-paste việc lặp lại, mất giờ làm OT, lương 15-20tr không đủ
3-6. **CỐT LÕI** (30-35s): Demo tool/workflow CỤ THỂ với số liệu. Scene 5 hoặc 6 BẮT BUỘC có câu "Tôi tự dùng cách này X tháng, tiết kiệm Y giờ/tuần..."
7. **CTA** (3-4s): Câu hỏi pattern interrupt để force comment, vd: "Bạn đã thử [tool] chưa? Comment 'YES'/'NO', mình gửi link setup miễn phí."
8. **SUBSCRIBE + DISCLAIMER** (3-4s): PHẢI có 2 thành phần
   - **Value prop subscribe** tailored theo topic: nói rõ giá trị người ta nhận khi subscribe (KHÔNG dùng câu generic)
   - **Disclaimer NHẸ** (không YMYL nữa): "Kết quả mỗi người khác nhau tùy workflow." HOẶC "Đây là chia sẻ cá nhân, các tool có thể đổi giá."

**Outro pattern chuẩn (Formula winning):**
```
"Subscribe [value prop cụ thể theo topic] — kênh đăng mỗi 6h sáng.
Kết quả mỗi người khác nhau tùy workflow."
```

Ví dụ value prop tailored theo pillar:
- **ai-tools:** "Subscribe để mỗi sáng có 1 prompt AI mới cho dân VP..."
- **automation:** "Subscribe nếu bạn cũng muốn auto-pilot công việc lặp lại..."
- **excel-ai:** "Subscribe để tự động hoá Excel report mất 3 tiếng → 30 giây..."
- **notion-productivity:** "Subscribe để hết phải lưu task ở 5 chỗ khác nhau..."

**Lý do thay đổi (27/05/2026 audit):** Channel "Tài Chính 5 Phút" 3 sub / 2.500 views = 0.12% conversion (benchmark 0.5-1%). Pivot sang automation niche LOW YMYL + outro value prop cụ thể tăng conversion 3-5x.

### Voiceover
- Mỗi scene 1-2 câu ngắn
- Dùng dấu chấm/phẩy đúng → TTS đọc có ngắt nghỉ tự nhiên
- KHÔNG viết "[disclaimer]" — viết tự nhiên trong scene 8
- Nói như bạn bè 28 tuổi nói với nhau, KHÔNG academic

### Visual keyword (TIẾNG ANH)
- 2-4 từ cụ thể, KHÔNG generic ("money", "business" — TỆ)
- Tốt: "hand counting cash vietnamese", "young office worker stressed", "stock chart green rising"
- 8 scene phải KHÁC nhau hoàn toàn (mix wide shot + close-up + abstract)

### Compliance niche mới (LOW risk, KHÔNG còn YMYL strict)
- ❌ KHÔNG promise tuyệt đối ("AI làm hết việc của bạn", "thay thế HR hoàn toàn")
- ❌ KHÔNG fake demo (mọi screenshot/workflow PHẢI realistic)
- ❌ KHÔNG nhắc đến giá tool sai (free tier có giới hạn, mention rõ)
- ✅ Disclaimer nhẹ scene 8: "Kết quả mỗi người khác nhau" / "Tool có thể đổi giá"
- ✅ Nếu nói số liệu ("tiết kiệm 80% thời gian") thì cần context: "với workflow N tasks lặp lại"

### Affiliate placeholder mới (replace finance link cũ)
Description dùng 3 placeholder:
- `[LINK_N8N]` — n8n cloud trial (affiliate khi đăng ký account)
- `[LINK_MAKE]` — Make.com affiliate (https://make.com/en/register?pc=tungpt)
- `[LINK_NOTION]` — Notion affiliate (premium tier 10% commission)

## File mẫu
Xem `data/scripts/6.json` — đây là sample đầu tiên user duyệt để chốt giọng văn.
