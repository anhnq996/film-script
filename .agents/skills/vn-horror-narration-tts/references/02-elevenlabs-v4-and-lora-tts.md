# 02. Hướng Dẫn ElevenLabs v4 Audio Tags & Chuẩn Bị Dataset LoRA 20 Phút

---

## 1. Prompt Tạo Giọng Kể Đêm Khuya (ElevenLabs Voice Design)

Dán prompt tiếng Anh này vào **Voices → Voice Design** để tạo giọng nền phù hợp nhất cho truyện ma tiếng Việt (sau đó chọn model **`Eleven v4`** khi đọc văn bản tiếng Việt):

```text
A mature Vietnamese male late-night radio storyteller in his late 30s, speaking close to a condenser microphone in a quiet dark room. Warm, deep, slightly husky baritone voice with a natural Southern Vietnamese conversational flow. Measured, unhurried pacing (~185 WPM), grounded and intimate like a close friend telling a true ghost story at midnight—calm and earthy during everyday scenes, dropping into a tense, hushed, chilling undertone during eerie moments without sounding theatrical or robotic.
```

### Cấu hình thanh trượt chuẩn cho `Eleven v4`
- **Model:** `Eleven v4` (hoặc `Eleven v3`; **không dùng** `Flash v2.5` hay `Multilingual v2` nếu giữ thẻ `[...]`).
- **Stability:** `38% – 45%` (đủ mở để ăn biểu cảm thở dài, thì thầm, hoảng loạn mà vẫn tròn dấu thanh tiếng Việt).
- **Similarity:** `80%`
- **Style Exaggeration:** `15% – 25%` (tránh kéo quá cao gây giọng kịch giả tạo).
- **Speed:** `0.92x` (hãm về khoảng `180–195` từ/phút).

---

## 2. Quy Tắc Gắn Audio Tags `[...]` Cho ElevenLabs v4

1. **Chỉ dùng ngoặc vuông `[...]`**, viết mô tả diễn xuất bằng tiếng Anh tự nhiên; không dùng `(...)`, `{...}` hoặc thẻ SSML `<break/>`.
2. **Đặt thẻ ngay trước câu/vế muốn đổi giọng**, và đặt thẻ phản ứng ngay sau câu nếu cần tiếng thở/cười ngắn.
3. **Kho thẻ ổn định cho truyện ma (dùng `2–4` thẻ / đoạn):**
   - **Mở đầu & đời thường:** `[warm, friendly, late-night radio host]`, `[conversational, grounded]`, `[relaxed, everyday tone]`, `[sighs softly]`.
   - **Gợn & cảnh báo:** `[low, serious tone]`, `[slowly, warning tone]`, `[uneasy, hushed]`, `[disgusted, grim]`, `[skeptical, scolding]`.
   - **Hoảng loạn & cao trào:** `[anxious, breathless]`, `[rushed, rising panic]`, `[trembling, terrified]`, `[sharp, dramatic]`, `[gasps softly]`, `[strained, urgent]`.
   - **Ám ảnh & kết treo:** `[whispers, stunned]`, `[slowly, visceral, horrified]`, `[exhales shakily]`, `[low, haunting, lingering suspense]`.
   - **Ngắt nhịp:** `[pause]`, `[long pause]`.

---

## 3. Quy Trình Render Dài 20 Phút Không Trôi Tông Giọng

- **Chia khối `250–400` từ/lần** (khoảng 2–3 đoạn văn) hoặc bật **Projects / Studio (Request Stitching)** để các đoạn kế tiếp giữ nguyên cao độ và âm sắc.
- **Chuẩn hóa văn bản trước khi dán:**
  - Xóa hết `*`, `_`, `#`.
  - Viết số hiệu và chữ cái đánh vần sang âm đọc tiếng Việt: `502` → `năm không hai`, `C - Ứ - U` → `Cờ... Ứ... U`.

---

## 4. Chuẩn Hóa Audio Mẫu Cho Pipeline Colab (`Demucs + Whisper + Seed-VC + LoRA`)

Khi dùng `extract_audio.py` hoặc trích mẫu từ YouTube để train LoRA (`colab/train_horror_voice_lora.ipynb`), giữ đúng thông số:
- **Khung cắt:** Bỏ `00:03:00` intro đầu (nhạc hiệu / chào kênh), lấy đúng `00:20:00` tiếp theo (`03:00 → 23:00`).
- **Định dạng:** `WAV PCM 16-bit` (`pcm_s16le`), `44.100 Hz`, `2` kênh (`stereo` để Demucs tách sạch vocal khỏi nhạc nền).
- **Lưu kèm transcript đối chiếu thời gian** dạng `[clip MM:SS | vid MM:SS]` để đối chiếu nhịp nghỉ thực của MC với kết quả Whisper cắt clip `3–15s`.
