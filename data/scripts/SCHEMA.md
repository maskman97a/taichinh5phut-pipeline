# Script JSON Schema — Tài Chính 5 Phút

Mỗi file `data/scripts/{idea_id}.json` phải đúng format dưới đây để pipeline assemble video chạy được.

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

### Scenes (8 cảnh, tổng 45-55s)
1. **HOOK** (3s, 8-12 từ): Câu hỏi shock hoặc tuyên bố tò mò có con số
2. **SETUP** (5-7s): Nỗi đau cụ thể của dân VP Việt
3-6. **CỐT LÕI** (30-35s): Giải pháp với số liệu cụ thể. Scene 5 hoặc 6 BẮT BUỘC có câu "Tôi áp dụng cách này X tháng và thấy..."
7. **CTA**: Câu tóm tắt hoặc câu hỏi mở để comment
8. **DISCLAIMER + Subscribe**: "Theo dõi để học mỗi ngày 1 mẹo tiền. Đây là góc nhìn cá nhân, không phải lời khuyên tài chính."

### Voiceover
- Mỗi scene 1-2 câu ngắn
- Dùng dấu chấm/phẩy đúng → TTS đọc có ngắt nghỉ tự nhiên
- KHÔNG viết "[disclaimer]" — viết tự nhiên trong scene 8
- Nói như bạn bè 28 tuổi nói với nhau, KHÔNG academic

### Visual keyword (TIẾNG ANH)
- 2-4 từ cụ thể, KHÔNG generic ("money", "business" — TỆ)
- Tốt: "hand counting cash vietnamese", "young office worker stressed", "stock chart green rising"
- 8 scene phải KHÁC nhau hoàn toàn (mix wide shot + close-up + abstract)

### YMYL Compliance
- KHÔNG khuyến nghị mã cổ phiếu cụ thể (vd: "mua HPG", "mua VIC")
- KHÔNG hứa hẹn ROI cụ thể ("chắc chắn lời 20%")
- Scene 8 PHẢI có disclaimer
- Pipeline sẽ tự append disclaimer dài vào description khi upload

## File mẫu
Xem `data/scripts/6.json` — đây là sample đầu tiên user duyệt để chốt giọng văn.
