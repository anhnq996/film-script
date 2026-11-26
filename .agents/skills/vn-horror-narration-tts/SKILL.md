---
name: vn-horror-narration-tts
description: >-
  Dẫn chuyện, chuẩn hóa nhịp kể 20 phút và chuyển kịch bản truyện ma tiếng Việt sang định dạng TTS
  (ElevenLabs v4 Audio Tags, Voice Design, và dataset VieNeu-TTS / Seed-VC LoRA) bằng cách phối hợp
  tinh hoa 4 kênh kể chuyện tâm linh nổi tiếng nhất: Chú Ba Duy, Đất Đồng Radio (Nguyễn Huy),
  HẺM Truyện Ma (MC Đình Soạn) và Người Dẫn Đường Cõi Âm (MC Duy Thuận). Use when the user asks
  for natural Vietnamese horror narration pacing (180–205 WPM), multi-channel hook/transition
  crafting, ElevenLabs v4 prompting with [...] audio tags, or preparing 20-minute WAV + transcript
  samples for Colab voice cloning.
---

# Kể Chuyện Ma Tự Nhiên Đa Kênh & Chuẩn Hóa TTS (ElevenLabs v4 / LoRA)

> **Mục tiêu cốt lõi:** Kết hợp sự gần gũi đời thực của **Chú Ba Duy**, nhịp radio đêm chậm rãi của **Nguyễn Huy**, kỹ thuật mở cảnh âm thanh – phân vai của **MC Đình Soạn**, và cách xoáy bi kịch nhân quả từ tựa truyện của **MC Duy Thuận** — tạo ra kịch bản **180–205 từ/phút** (`3.600–4.100` từ cho video `20` phút) đọc nghe mượt tai trên cả **ElevenLabs v4** lẫn giọng người thật / **VieNeu-TTS + Seed-VC LoRA**.

---

## 1. Bảng Điều Hướng Tài Liệu

| Tác vụ | Tài liệu trong skill | Nội dung chính |
|---|---|---|
| **Chọn nhịp kể, cách mở bài, chuyển cảnh & giọng vùng miền** | [01-four-channel-style-matrix.md](./references/01-four-channel-style-matrix.md) | Bảng số liệu đo từ 558 tập của 4 kênh, 4 kiểu mở đầu thật (đã sửa lỗi ASR), 4 kỹ thuật nối mạch tự nhiên. |
| **Xuất kịch bản cho ElevenLabs v4 hoặc chuẩn bị audio train LoRA** | [02-elevenlabs-v4-and-lora-tts.md](./references/02-elevenlabs-v4-and-lora-tts.md) | Prompt Voice Design, thông số thanh trượt `Eleven v4`, kho `[...]` Audio Tags, chuẩn hóa số/chữ cái tiếng Việt, thông số `WAV 44.1kHz`. |
| **Xem bài mẫu hoàn chỉnh Mode A vs Mode C (`Eleven v4`)** | [sample-cau-co-elevenlabs-v4.md](./examples/sample-cau-co-elevenlabs-v4.md) | Trích đoạn truyện cầu cơ *"Đồng Xu Dính Đất Huyệt"* bản đọc sạch và bản gắn sẵn Audio Tags `Eleven v4`. |

---

## 2. Công Thức Phối Hợp 4 Giọng Kể Cho Video 20 Phút (`~3.700 – 4.000` Từ)

1. **00:00 – 01:30 (Mở đầu & Hook):**
   - Dùng vòng tròn xưng hô thân mật **`mình` / `mọi người`** (Chú Ba Duy) + **đặt câu hỏi điều tra trực tiếp từ tựa truyện** (Duy Thuận) + **nhịp đệm `"Ờ..."`** trước khi bước vào bối cảnh (Nguyễn Huy) + **giờ giấc chiều tà kèm âm thanh sinh hoạt** (Đình Soạn).
2. **01:30 – 08:00 (Đời thực & Tội lỗi con người):**
   - Giữ tốc độ kể chậm **`180–205` từ/phút** để người nghe ban đêm theo kịp mà không bị ngộp.
   - Đẩy mâu thuẫn đời thường (tiền bạc, nợ nần, ghen tuông, gia đình) trước khi có dị tượng; điều chỉnh mật độ đại từ Nam Bộ (`ổng/bả/cổ/ảnh`) ở mức **`60–80 / 10k` từ** nếu muốn khán giả 3 miền nghe dễ chịu, hoặc **`150+ / 10k` từ** nếu làm thuần chất miền Tây.
3. **08:00 – 16:00 (Leo thang tâm linh & Thoại nhân vật):**
   - Áp dụng **kể xen thoại 3 lớp** (không dùng nhãn thoại kịch `NHÂN VẬT:`), gắn thêm **hành động bật nguồn sáng / mở cửa / nghe tiếng động** kiểu Đình Soạn làm điểm neo cắt cảnh hình ảnh 2.5D.
4. **16:00 – 20:00 (Cao trào bóc lớp & Hậu vị):**
   - Tả hiện trường theo thứ tự **từ ngoài vào trong** kiểu Nguyễn Huy kết hợp ví von vật chất bình dân kiểu Chú Ba Duy; khép lại bằng chiêm nghiệm nhân quả mộc mạc kiểu Duy Thuận, không rao giảng.

---

## 3. Checklist Chuẩn Hóa Bắt Buộc Trước Khi Đưa Vào TTS

- [ ] **Xóa 100% ký tự định dạng markdown** (`*`, `_`, `#`, `` ` ``) để bộ đọc không vấp hoặc đổi giọng bất thường.
- [ ] **Phiên âm số hiệu & chữ đánh vần sang tiếng Việt:** `502` → `năm không hai`, `C - Ứ - U` → `Cờ... Ứ... U`, `100%` → `một trăm phần trăm`.
- [ ] **Chỉ dùng ngoặc vuông `[...]` cho Audio Tags tiếng Anh trên `Eleven v3 / Eleven v4`** — tuyệt đối không dùng `(...)` hay `<break .../>`, và không dùng `[...]` nếu render bằng model cũ (`Multilingual v2`, `Flash v2.5`).
- [ ] **Ngắt dòng theo nhịp thở (6–14 chữ/vế)** dùng dấu phẩy `,` và dấu chấm lửng `...` để giữ tự nhiên, không dồn câu 40 chữ không dấu ngắt.
- [ ] **Cắt khối `250–400` từ mỗi lượt tạo audio** (hoặc bật *Request Stitching* trong Studio) để giữ ổn định âm sắc suốt 20 phút.
