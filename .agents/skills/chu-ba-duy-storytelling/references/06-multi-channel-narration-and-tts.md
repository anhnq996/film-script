# 06. Phối Hợp Đa Kênh (4 Giọng Kể) & Xuất Kịch Bản Cho ElevenLabs v4 / TTS

Tài liệu bổ trợ cho `chu-ba-duy-storytelling`, tổng hợp từ [05-multi-channel-natural-narration.md](../../../analysis/05-multi-channel-natural-narration.md) để điều chỉnh nhịp kể 20 phút cho audio nghe đêm và xuất kịch bản sẵn sàng cho **ElevenLabs v4 (`Eleven v4`)** hoặc pipeline **VieNeu-TTS / Seed-VC LoRA**.

---

## 1. Bảng Đối Chiếu Nhịp Kể & Khẩu Ngữ 4 Kênh

| Kênh / Giọng kể | Mẫu đo | Tốc độ trung vị (WPM) | Xưng hô chủ đạo (`/10k từ`) | Đại từ Nam Bộ vs Phổ thông (`/10k từ`) | Thế mạnh ghép vào Chú Ba Duy |
|---|---|---:|---|---|---|
| **Chú Ba Duy** (`@chuyenmachu3duy`) | 531 tập | **240,0** *(190,7–362,9)* | `mình` **70,5** \| `mọi người` **17,7** | `ổng/bả/cổ/ảnh`: **181,2** vs `ông ấy...`: **3,3** | Khẩu ngữ đời thực, van xả ấm áp, 12 thiết luật nhân quả |
| **Đất Đồng Radio — Nguyễn Huy** | 10 tập | **177,9** *(160,0–187,6)* | `mình` 37,9 \| `tôi` 33,9 \| `mọi người` 7,8 | `ổng/bả/cổ/ảnh`: **64,4** vs `ông ấy...`: **15,9** | Nhịp chậm nghe đêm, nhịp đệm `"Ờ..."`, tả hiện trường bóc lớp |
| **HẺM Truyện Ma — MC Đình Soạn** | 10 tập | **202,4** *(160,4–216,0)* | `tôi` **65,1** \| `mình` 36,0 \| `quý vị` 5,2 | `ổng/bả/cổ/ảnh`: **52,8** vs `ông ấy...`: **24,9** | Mở cảnh bằng âm thanh & giờ giấc chiều tà, chuyển cảnh điện ảnh |
| **Người Dẫn Đường Cõi Âm — Duy Thuận** | 7 tập | **186,0** *(178,5–194,5)* | `mình` 38,9 \| `tôi` 36,8 \| `quý vị` 2,9 | `ổng/bả/cổ/ảnh`: **47,2** vs `ông ấy...`: **13,1** | Câu hỏi điều tra ngay từ tựa truyện, tâm lý bi kịch gia đình |

---

## 2. Nhịp Vàng Cho Kịch Bản 20 Phút (`180–205` Từ/Phút)

- Khi viết cho **TTS / nghe đêm thư giãn**, hãm mật độ chữ từ `240` từ/phút xuống còn **`180–205` từ/phút** (`3.600 – 4.100` từ cho video `20` phút) để chừa khoảng thở cho giọng trầm và hiệu ứng 2.5D.
- **Mở đầu Hybrid:** Giữ lời chào `mình / mọi người` của Chú Ba Duy + câu hỏi treo ngay từ tựa đề kiểu Duy Thuận + nhịp đệm `"Ờ..."` kiểu Nguyễn Huy + mốc giờ chiều tà và âm thanh xóm làng kiểu Đình Soạn.
- **Độ đậm phương ngữ tùy khán giả:** Nếu muốn phục vụ khán giả cả 3 miền nghe êm lâu, hạ mật độ đại từ Nam Bộ từ `181/10k` xuống vùng trung dung **`60–80/10k`** (giống Nguyễn Huy) nhưng giữ nguyên cú pháp khẩu ngữ (`ngặt một cái`, `nhưng mà`, `đứng hình`).

---

## 3. Chuẩn Hóa Văn Bản Cho ElevenLabs v4 & VieNeu-TTS

1. **Dùng ElevenLabs v4 (`Eleven v4`) Audio Tags bằng tiếng Anh trong ngoặc vuông `[...]`:**
   - Đặt tag **ngay trước** câu/vế cần đổi sắc thái: `[warm, friendly]`, `[low, serious tone]`, `[slowly, suspenseful]`, `[whispers]`, `[trembling, terrified]`, `[sighs softly]`, `[pause]`, `[long pause]`.
   - **Tuyệt đối không dùng** ngoặc tròn `(...)`, ngoặc nhọn `<break .../>` (SSML cũ), hay chọn nhầm model `Flash v2.5` / `Multilingual v2` (các model cũ sẽ đọc thành tiếng chữ trong ngoặc vuông).
2. **Sạch ký tự & viết thành âm đọc tiếng Việt:**
   - Xóa sạch `*`, `_`, `#` markdown trong văn bản đọc.
   - Đổi số hiệu và chữ cái đánh vần sang âm tiếng Việt (`502` → `năm không hai`, `C - Ứ - U` → `Cờ... Ứ... U`, `4,5 triệu` → `bốn triệu rưỡi`).
3. **Chia đoạn khi render dài:**
   - Cắt mỗi lần render khoảng **`250–400` từ** (hoặc dùng chế độ Projects/Studio bật nối ngữ cảnh) để tránh bị trôi tông giọng ở nửa sau video `20` phút.
   - Thanh trượt gợi ý trên Eleven v4: `Stability 38%–45%`, `Similarity 80%`, `Style Exaggeration 15%–25%`, `Speed 0.92x`.
