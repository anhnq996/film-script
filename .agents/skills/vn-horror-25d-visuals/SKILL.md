---
name: vn-horror-25d-visuals
description: >-
  Thiết kế và lập trình phần hình ảnh nền 2D kết hợp hiệu ứng 2.5D bằng code (HTML5 Canvas, CSS
  parallax, WebAudio ambience) cho video kể chuyện ma – tâm linh tiếng Việt dài 20–90 phút hoặc
  video ngắn TikTok/Shorts. Use when the user asks how to animate static 2D/AI horror backgrounds,
  build a 2.5D web/Remotion horror scene, add fog/rain/incense smoke/oil-lamp flicker/vignette/grain,
  or decide between Google Flow AI video clips vs. 2D + code animation for spiritual storytelling.
---

# Hình Ảnh 2D + Code Animation 2.5D Cho Video Kể Chuyện Ma

> **Nguyên tắc cốt lõi:** Với video kể chuyện nghe đêm dài **20–90 phút**, tuyệt đối tránh 2 thái cực: (1) dùng code rig nhân vật 2D cử động (nhìn giả, mất chất rợn) và (2) nối hàng trăm clip AI liên tục (tốn credit, dễ méo mặt và gây mỏi mắt). Công thức giữ chân tốt nhất là **ảnh nền bán thực giàu không khí + code thổi hồn môi trường (Ambient 2.5D)**.

---

## 1. Tỷ Trọng Hình Ảnh Theo Thời Lượng Kênh

| Định dạng | Tỷ trọng khuyến nghị | Chiến lược triển khai |
|---|---|---|
| **YouTube dài (20–90 phút)** | **20% AI Video (Google Flow) + 80% 2D/2.5D Code VFX** | Dùng 3–5 cảnh Google Flow cho **15–30 giây Hook mở đầu**; phần thân dùng **5–8 bối cảnh 2D** tách lớp tiền cảnh + hiệu ứng thời tiết/ánh sáng chạy chậm bằng code. |
| **Shorts / TikTok (1–3 phút)** | **80% Google Flow nối cảnh + 20% Code hậu kỳ** | Đổi khung mỗi 3–5s bằng góc máy POV, bóng lưng, thiếu sáng; dùng code phủ film grain, rung nhẹ khi sấm chớp và phụ đề theo nhịp. |

---

## 2. Kiến Trúc Lớp Sân Khấu 2.5D (`1920x1080`, 16:9)

Thứ tự xếp lớp từ sau ra trước (`z-index` tăng dần):

1. **Lớp nền (`layer-bg`):** Ảnh phong cảnh 16:9 tông tối xanh rêu – hổ phách (`teal/amber desaturated`), tuyệt đối không rõ mặt người. Chuyển động đẩy máy/pan siêu chậm (`scale 1.00 → 1.15` trong `10s`).
2. **Lớp ánh sáng gắn tọa độ (`moon-glow`, `window-glow`, `lamp-glow`):** Radial gradient dùng `mix-blend-mode: screen`. Áp dụng **cùng ma trận `translate/scale`** với ảnh nền để đốm sáng không bị trượt khỏi cửa sổ hay ngọn đèn khi camera zoom.
3. **Lớp tiền cảnh tách nền (`layer-fg`, `mix-blend-mode: multiply`):**
   - Dùng ảnh silhouette **đen tuyền `#000000` trên nền trắng tuyền `#FFFFFF`** (cỏ lau dưới đáy, khóm trúc hai rìa khung).
   - Luôn thêm `filter: contrast(1.25) brightness(1.04)` để ép nền trắng gần-tuyệt-đối (`#fefefe` do nén JPEG) về `#ffffff`, giúp biến mất 100% khi multiply.
   - Di chuyển tiền cảnh nhanh hơn nền `1.5x–2.5x` + lắc nhẹ theo `sin(t)` để tạo chiều sâu thị sai (parallax).
4. **Canvas VFX (`fx-canvas`):**
   - **Sương mù 2 tầng:** 2 dải radial gradient trôi ngang trái chiều ở tốc độ khác nhau.
   - **Mưa xiên:** Các nét mảnh nghiêng góc nhỏ (`~16%` x theo y), giảm mật độ một nửa trên màn hình nhỏ `< 900px`.
   - **Khói nhang (`globalCompositeOperation = 'lighter'`):** Hạt sinh từ tọa độ đầu nhang **đã chiếu qua transform zoom/pan của nền (`projectPoint`)**, uốn lượn theo `fbm1D(seed + age)` rồi tan dần.
   - **Bụi lơ lửng (`screen`):** Đốm sáng ấm li ti bay chậm quanh đèn dầu.
5. **Hậu kỳ & Điểm nhấn kinh dị:**
   - **Đèn dầu lập lòe:** Dùng `1D value noise / fbm` điều biến đồng thời độ mờ `lamp-glow` và `brightness()` của ảnh nền.
   - **Nhịp tắt đèn / Bóng mờ:** Vụ tắt đèn cửa sổ đột ngột hoặc bóng mờ lướt ở khung cửa tối (`opacity` tăng nhẹ rồi tắt), đi kèm **siết hẹp `vignette`** và hạ `master brightness`.
   - **Film Grain:** Canvas nhỏ (`240x135`) vẽ nhiễu ngẫu nhiên cập nhật mỗi 2 frame (`opacity ~0.085`, `overlay`).
   - **Chuyển cảnh qua nền đen:** Crossfade `0.6s` xuống đen rồi `0.6s` mở cảnh mới.

---

## 3. Âm Thanh Nền Tổng Hợp & Đóng Gói MP4

- **WebAudio chạy trên web:** Trộn nhiễu trắng lọc băng thông (mưa ngoài trời vs mưa nghe từ trong nhà), 2 oscillator lệch tần ~`55Hz` tạo tiếng ù trầm (`low drone`), xung trầm cho tiếng sấm và tiếng rít cao nhẹ ở cảnh bàn thờ. Đồng bộ pause/seek qua `AudioContext.suspend()` / `resume()` và reset cờ one-shot khi tua.
- **Tối ưu hiệu năng:** Giới hạn `devicePixelRatio` ở `1.5`, ưu tiên CSS `transform: translate3d(...) scale(...)` cho ảnh lớn để GPU xử lý.
- **Lộ trình xuất video 20 phút:** Khi đã chốt giao diện web/Canvas, dùng **Remotion** hoặc **Puppeteer + FFmpeg** chụp từng frame theo đồng hồ `t` cố định (`30fps`) rồi ghép với file audio giọng đọc đã xử lý.
