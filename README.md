# YouTube Channel Transcript Crawler (No API)

Công cụ quét kênh YouTube **không cần YouTube Data API**, tự động phân loại video theo `playlists/` và `other/`, và xuất transcript sạch cho từng ngôn ngữ có sẵn trong thư mục riêng của từng video.

## Yêu cầu

- Python 3.9+ (chỉ dùng thư viện chuẩn)
- `yt-dlp` đã cài sẵn trong PATH

## Cấu trúc thư mục đầu ra

```text
output/
└── <Tên kênh> [<channel_id>]/
    ├── channel_info.json
    ├── playlists/
    │   └── <Tên Playlist>/
    │       ├── _playlist.json
    │       └── 001 - <Tiêu đề video> [<video_id>]/
    │           ├── info.json
    │           ├── en.txt
    │           └── vi.txt
    └── other/
        └── 001 - <Tiêu đề video> [<video_id>]/
            ├── info.json
            └── en.txt
```

- **Tránh trùng lặp:** Nếu một video nằm trong nhiều playlist, tool chỉ tải transcript 1 lần rồi ghi vào từng thư mục playlist tương ứng. Video nào thuộc kênh nhưng không nằm trong playlist nào sẽ vào `other/`.
- **Ngôn ngữ mặc định (`auto`):** Lấy toàn bộ phụ đề thủ công (manual) mọi ngôn ngữ + phụ đề tự động gốc của video (không tải tràn lan hàng trăm bản dịch máy), ưu tiên manual nếu trùng ngôn ngữ.
- **Resume tự động:** Chạy lại cùng kênh sẽ tự bỏ qua các video đã có sẵn `info.json` (trừ khi truyền `--force`).

## Cách dùng

### 1. Chế độ tương tác (nhập link khi chạy)

```bash
./run.sh
```

Hoặc:

```bash
python3 crawler.py
```

### 2. Chế độ dòng lệnh

```bash
# Quét toàn bộ kênh (lấy tất cả ngôn ngữ manual + auto gốc)
python3 crawler.py "https://www.youtube.com/@3blue1brown"

# Chỉ định ngôn ngữ cụ thể, thêm mốc thời gian [MM:SS], quét cả Shorts
python3 crawler.py "https://www.youtube.com/@3blue1brown" --langs vi,en --timestamps --include-shorts

# Chạy thử nhanh: tối đa 2 playlist đầu, mỗi playlist/tab tối đa 3 video
python3 crawler.py "https://www.youtube.com/@3blue1brown" --playlist-limit 2 --limit 3

# Xuất thêm file .srt và dùng cookies trình duyệt nếu bị chặn bot-check
python3 crawler.py "https://www.youtube.com/@tenkenh" --srt --cookies-from-browser chrome
```

## Các tuỳ chọn chính

| Cờ | Ý nghĩa |
|---|---|
| `-o, --output` | Thư mục gốc lưu kết quả (mặc định: `./output`) |
| `--langs` | Danh sách mã ngôn ngữ cách nhau bởi dấu phẩy (vd `vi,en`) hoặc `auto` |
| `--include-shorts` | Quét thêm tab `/shorts` vào `other/` |
| `--include-streams` | Quét thêm tab `/streams` vào `other/` |
| `--playlist-limit N` | Giới hạn tối đa N playlist |
| `--limit N` | Giới hạn tối đa N video mỗi playlist / tab |
| `--sleep S` | Thời gian nghỉ (giây) giữa mỗi video (mặc định `1.0`) |
| `--timestamps` | Thêm mốc thời gian `[MM:SS]` vào đầu dòng trong `.txt` |
| `--srt` | Lưu thêm file phụ đề `.srt` |
| `--force` | Tải lại kể cả các video đã có sẵn |
| `--cookies` / `--cookies-from-browser` | Dùng cookies nếu YouTube yêu cầu đăng nhập |
