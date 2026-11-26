# Hướng Dẫn Vận Hành Google Colab Cho AI Agent (Train Giọng Kể Chuyện Ma + Render Full Audio)

Tài liệu này là quy trình thực thi từng bước dành cho **AI Agent** thao tác trên **Google Drive + Google Colab** để:
1. Train mô hình giọng kể chuyện ma tiếng Việt có nhịp nhấn nhá tự nhiên (**Seed-VC + VieNeu-TTS v3 Turbo LoRA**) từ file audio mẫu 27 phút 51 giây đã chuẩn bị sẵn.
2. Lưu vĩnh viễn mô hình đã merge về Google Drive.
3. Render toàn bộ kịch bản truyện ma `demo_script_cai_nap_hom_bo_kinh.txt` (~19,6 phút) thành file `.wav` 48kHz hoàn chỉnh.

---

## 1. Cấu Trúc Thư Mục Trong Gói Này

```text
horror_voice_colab_bundle/
├── AI_COLAB_INSTRUCTIONS.md                     # File hướng dẫn này
├── train_horror_voice_lora.ipynb                # Notebook Google Colab chạy trọn gói
├── 00_source/
│   └── source_20min.wav                         # Audio mẫu đã cắt ghép sẵn (27p51s, 44.1kHz stereo, 3 sắc thái)
├── scripts/
│   └── demo_script_cai_nap_hom_bo_kinh.txt      # Kịch bản sạch không tiêu đề markdown (4.711 từ, ~19,6 phút)
└── skill_chu_ba_duy/                            # Bộ skill viết kịch bản (nếu cần viết/chỉnh thêm truyện mới)
```

---

## 2. Bước 1 — Chuẩn Bị File Trên Google Drive (ĐÚNG ĐƯỜNG DẪN)

Trước khi chạy notebook, upload **2 file sau** lên Google Drive đúng cấu trúc thư mục:

1. Tạo thư mục trên Google Drive: `MyDrive/horror_voice_lora/00_source/` và `MyDrive/horror_voice_lora/06_renders/`.
2. Upload `00_source/source_20min.wav` vào đúng đường dẫn:
   ```text
   MyDrive/horror_voice_lora/00_source/source_20min.wav
   ```
   > **QUAN TRỌNG:** Phải giữ nguyên tên file là **`source_20min.wav`**. Khi file này đã nằm sẵn tại đúng đường dẫn trên và `FORCE_REEXTRACT = False`, **Bước 0** trong notebook sẽ tự động bỏ qua bước tải YouTube và giữ nguyên **toàn bộ 27 phút 51 giây** (không cắt mất 3 phút đầu, không cắt ngắn về 20 phút).
3. Upload `scripts/demo_script_cai_nap_hom_bo_kinh.txt` vào:
   ```text
   MyDrive/horror_voice_lora/06_renders/demo_script_cai_nap_hom_bo_kinh.txt
   ```

---

## 3. Bước 2 — Mở Google Colab & Thiết Lập GPU

1. Truy cập `https://colab.research.google.com/`.
2. Chọn **File → Upload notebook** → tải file `train_horror_voice_lora.ipynb` lên.
3. Đổi Runtime GPU (**BẮT BUỘC**):
   - Vào menu **Runtime → Change runtime type**.
   - Chọn **Hardware accelerator: L4 GPU** (24GB VRAM — tối ưu nhất; chỉ dùng T4 nếu tài khoản không có L4).
   - Bấm **Save**.

---

## 4. Bước 3 — Thực Thi Tuần Tự Từng Cell & Điều Kiện Kiểm Đạt (Pass Check)

Chạy từng cell từ trên xuống dưới, **chỉ chuyển sang cell kế tiếp khi cell hiện tại hoàn tất không lỗi**:

### Cell 1 — `⚙️ 1. Kết nối Google Drive & Cấu hình Pipeline`
- **Tham số chuẩn (giữ nguyên hoặc điền đúng):**
  - `PROJECT_DIR = "/content/drive/MyDrive/horror_voice_lora"`
  - `FORCE_REEXTRACT = False`
  - `NEW_VOICE_NAME = "Giong_Ke_Chuyen_Ma"`
  - `SEEDVC_F0_CONDITION = True` *(BẮT BUỘC `True` để giữ đường cao độ & nhịp nhấn nhá)*
  - `SEEDVC_DIFFUSION_STEPS = 30`
  - `SEEDVC_SEMI_TONE_SHIFT = 0`
  - `LORA_EPOCHS = 3` *(có thể đặt `4` nếu muốn nhịp nhấn đậm hơn; không nên quá `5` để tránh overfit)*
  - `LORA_RANK = 16`
- **Thao tác:** Cho phép cấp quyền mount Google Drive khi Colab hiện popup.
- **Pass check:** In ra `Đã tạo thư mục làm việc trên Google Drive: /content/drive/MyDrive/horror_voice_lora` và `!nvidia-smi` hiển thị GPU (`L4` hoặc `T4`).

### Cell 2 — `✂️ Trích xuất audio & cắt đúng 20 phút` (Bước 0)
- **Pass check:** Phải in ra:
  - `✅ Đã có sẵn file 20 phút: /content/drive/MyDrive/horror_voice_lora/00_source/source_20min.wav`
  - `Thời lượng: 27.85 phút`
- **Nếu lỗi:** Nếu cell cố tải YouTube, dừng ngay và kiểm tra lại file `source_20min.wav` đã nằm đúng ở `MyDrive/horror_voice_lora/00_source/source_20min.wav` chưa.

### Cell 3 — `📦 1A. Cài VieNeu-TTS v3 Turbo & Liệt kê giọng miễn phí` (Bước 1A)
- **Thời gian:** ~2–3 phút.
- **Pass check:** In ra danh sách các giọng có sẵn `[00] ...`, `[01] ...` và lưu `/tmp/vieneu_voices.json`.

### Cell 4 — `🎙️ 1B. Chọn 1 giọng nam trầm miễn phí & Xuất target_voice.wav` (Bước 1B)
- **Gợi ý chọn giọng:** Xem danh sách ở Cell 3, ưu tiên điền đúng tên **1 giọng nam miền Nam / nam trầm** vào `TARGET_PRESET_VOICE` (hoặc để trống `""` để notebook tự chọn giọng nam đầu tiên).
- **Pass check:** Xuất thành công `/content/drive/MyDrive/horror_voice_lora/01_target_voice/target_voice.wav` và hiện trình phát Audio nghe thử 10 giây.

### Cell 5 — `🧹 Chạy Demucs (htdemucs) tách vocal sạch` (Bước 2A)
- **Thời gian:** ~2 phút trên L4.
- **Pass check:** Tạo thành công `/content/drive/MyDrive/horror_voice_lora/02_vocals/vocals_20min.wav` (44.1kHz mono sạch nhạc nền).

### Cell 6 — `📝 Cắt vocal thành các câu 3.2s – 14.0s bằng Whisper large-v3` (Bước 2B)
- **Thời gian:** ~2–3 phút trên L4.
- **Pass check:** In ra `🎉 Đã cắt xong <N> clip sạch (3–15s)` (thường khoảng **200–320 clips** cho 27,85 phút audio) và lưu `03_source_clips/clips_meta.json`.

### Cell 7 — `🔄 Cài Seed-VC & Chuyển toàn bộ clip sang giọng miễn phí VieNeu-TTS` (Bước 2C)
- **Thời gian:** ~5–9 phút trên L4 (có hỗ trợ tự resume nếu bị ngắt).
- **Pass check:** In ra `Hoàn tất Seed-VC: <N>/<N> clips.` và xuất `/content/drive/MyDrive/horror_voice_lora/04_dataset/metadata.csv`.
- **Tối ưu chất lượng (khuyến nghị trước khi sang Cell 8):** Nếu có thể sửa file `04_dataset/metadata.csv` trên Drive, rà nhanh các lỗi ASR phổ biến của giọng Miền Tây để LoRA học chính tả & dấu câu chuẩn hơn:
  - `dong hồn` → `vong hồn`
  - `cắn lữ` → `cắn lưỡi`
  - `đám cứ` → `đám cưới`
  - `cậu bẫy` → `cậu Bảy`
  - `mã` (chỉ mộ phần) → `mả`
  - Giữ lại đầy đủ dấu `...`, `?`, `!` vì LoRA học lên/xuống giọng trực tiếp từ dấu câu.

### Cell 8 — `🚀 Chuẩn bị train.parquet, Train LoRA, Merge Model & Lưu về Drive` (Bước 3 & 4)
- **Thời gian:** ~10–18 phút trên L4.
- **Pass check:** In ra `🎉 HOÀN TẤT TRAIN LORA! Model của bạn đã lưu vĩnh viễn tại: /content/drive/MyDrive/horror_voice_lora/05_trained_model/merged`.

### Cell 9 — `🎧 Nghe thử giọng kể chuyện ma mới` (Bước 5A)
- **Pass check:** Xuất thành công `06_renders/test_horror_sample.wav` và phát thử được trên Colab.

### Cell 10 — `📖 Render toàn bộ file kịch bản .txt thành WAV hoàn chỉnh` (Bước 5B)
- **Điền tham số:**
  - `STORY_TXT_PATH = "/content/drive/MyDrive/horror_voice_lora/06_renders/demo_script_cai_nap_hom_bo_kinh.txt"`
  - `OUTPUT_STORY_WAV = "/content/drive/MyDrive/horror_voice_lora/06_renders/cai_nap_hom_bo_kinh_full.wav"`
- **Thời gian:** ~3–6 phút trên L4.
- **Pass check:** In ra `🎉 Hoàn tất! Đã lưu: .../06_renders/cai_nap_hom_bo_kinh_full.wav` với thời lượng khoảng `18–21 phút` (48kHz WAV).

---

## 5. Xử Lý Sự Cố & Bắt Buộc Ngắt Runtime Khi Xong

1. **Colab mất kết nối hoặc hết RAM giữa chừng:**
   - Chọn **Runtime → Restart session** (giữ nguyên L4 GPU).
   - Chạy lại **Cell 1** (Mount Drive) và chạy lại **Cell 3** (nếu cần cài lại `VieNeu-TTS` trong `/content/VieNeu-TTS` khi cấp máy mới).
   - Chạy tiếp ngay tại cell bị dừng — mọi bước trước đã lưu trên Google Drive (`FORCE_REEXTRACT = False`, Seed-VC tự bỏ qua các clip đã convert).
2. **Muốn giọng nhấn nhá mạnh hơn hoặc đầm hơn khi render (Cell 9 & Cell 10):**
   - Trong code gọi `tts.infer(..., temperature=0.8)`: tăng nhẹ lên `0.85` để giàu biến thiên cảm xúc hơn, hoặc giảm xuống `0.72` nếu thấy câu dài hơi vấp.
3. **BẮT BUỘC SAU KHI HOÀN TẤT:**
   - Kiểm tra file `05_trained_model/merged` và `06_renders/cai_nap_hom_bo_kinh_full.wav` đã nằm yên trên Google Drive.
   - Vào **Runtime → Disconnect and delete runtime** ngay lập tức để không bị trừ Compute Units oan!
