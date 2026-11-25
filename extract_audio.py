#!/usr/bin/env python3
"""
Trích xuất âm thanh từ file video/audio hoặc link YouTube và cắt đoạn kể 20 phút
(mặc định bỏ 3 phút đầu intro, lấy 20 phút tiếp theo) để chuẩn bị dữ liệu tách vocal
và học nhịp kể trên Google Colab.

Yêu cầu:
  - ffmpeg trong PATH
  - yt-dlp trong PATH (chỉ cần nếu đầu vào là link URL)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_hms_to_seconds(value: str) -> int:
    """Parse HH:MM:SS, MM:SS, or raw seconds into integer seconds."""
    raw = value.strip()
    if raw.isdigit():
        return int(raw)
    parts = raw.split(":")
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(float(s))
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(float(s))
    raise ValueError(f"Định dạng thời gian không hợp lệ: {value!r} (dùng HH:MM:SS hoặc MM:SS)")


def format_seconds_hms(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def require_binary(name: str, install_hint: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Không tìm thấy `{name}` trong PATH. Cài đặt: {install_hint}")
    return path


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def probe_duration(audio_path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def cut_with_ffmpeg(
    input_path: Path,
    output_wav: Path,
    start_sec: int,
    duration_sec: int,
    sample_rate: int,
    channels: int,
    skip_seek: bool = False,
) -> None:
    require_binary("ffmpeg", "sudo apt-get install -y ffmpeg")
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]
    if not skip_seek and start_sec > 0:
        cmd.extend(["-ss", format_seconds_hms(start_sec)])
    cmd.extend(["-i", str(input_path)])
    if duration_sec > 0:
        cmd.extend(["-t", str(duration_sec)])
    cmd.extend(
        [
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            str(output_wav),
        ]
    )
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi với mã thoát {proc.returncode}")


def build_ytdlp_extra_args() -> list[str]:
    extra: list[str] = []
    if shutil.which("deno"):
        extra.extend(["--js-runtimes", "deno", "--remote-components", "ejs:github"])
    elif shutil.which("node"):
        extra.extend(["--js-runtimes", "node", "--remote-components", "ejs:github"])
    return extra


def download_and_cut_url(
    url: str,
    output_wav: Path,
    start_sec: int,
    duration_sec: int,
    sample_rate: int,
    channels: int,
    lang: str = "vi",
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
) -> None:
    require_binary("yt-dlp", "pip install -U yt-dlp")
    require_binary("ffmpeg", "sudo apt-get install -y ffmpeg")

    auth_args: list[str] = build_ytdlp_extra_args()
    if cookies:
        auth_args.extend(["--cookies", cookies])
    if cookies_from_browser:
        auth_args.extend(["--cookies-from-browser", cookies_from_browser])

    # Ưu tiên bản tiếng gốc (tránh bị YouTube tự chọn bản lồng tiếng AI en-US)
    fmt_selector = (
        f"bestaudio[language^={lang}]/bestaudio[format_note*=original]/bestaudio/best"
        if lang
        else "bestaudio[format_note*=original]/bestaudio/best"
    )

    end_sec = start_sec + duration_sec
    section_spec = f"*{format_seconds_hms(start_sec)}-{format_seconds_hms(end_sec)}"

    with tempfile.TemporaryDirectory(prefix="extract_audio_") as tmpdir:
        tmp_template = str(Path(tmpdir) / "raw.%(ext)s")

        # Ưu tiên tải đúng đoạn 20 phút bằng --download-sections cho nhanh
        print(f"[1/2] Đang tải đoạn audio {section_spec} (format: {fmt_selector}) từ URL...")
        section_cmd = [
            "yt-dlp",
            "-f",
            fmt_selector,
            "--no-playlist",
            "--download-sections",
            section_spec,
            "--force-keyframes-at-cuts",
            "-o",
            tmp_template,
            *auth_args,
            url,
        ]
        proc = subprocess.run(section_cmd)
        downloaded = [p for p in Path(tmpdir).glob("raw.*") if p.is_file() and p.stat().st_size > 0]

        skip_seek = True
        if proc.returncode != 0 or not downloaded:
            print("[!] --download-sections không khả dụng cho video này, chuyển sang tải full audio rồi cắt...")
            full_cmd = [
                "yt-dlp",
                "-f",
                fmt_selector,
                "--no-playlist",
                "-o",
                tmp_template,
                *auth_args,
                url,
            ]
            proc2 = subprocess.run(full_cmd)
            downloaded = [p for p in Path(tmpdir).glob("raw.*") if p.is_file() and p.stat().st_size > 0]
            if proc2.returncode != 0 or not downloaded:
                raise RuntimeError(
                    "Không thể tải audio từ URL. Nếu YouTube yêu cầu xác minh, "
                    "hãy truyền thêm --cookies cookies.txt hoặc --cookies-from-browser chrome."
                )
            skip_seek = False

        src_file = downloaded[0]
        print(f"[2/2] Đang chuẩn hoá WAV ({sample_rate}Hz, {channels}ch) -> {output_wav}")
        cut_with_ffmpeg(
            input_path=src_file,
            output_wav=output_wav,
            start_sec=start_sec,
            duration_sec=duration_sec,
            sample_rate=sample_rate,
            channels=channels,
            skip_seek=skip_seek,
        )


def list_output_videos(output_root: Path) -> list[dict]:
    videos: list[dict] = []
    if not output_root.exists():
        return videos
    for info_path in sorted(output_root.rglob("info.json")):
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("url"):
            videos.append(data)
    return videos


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trích xuất âm thanh từ video/URL và cắt đoạn kể 20 phút chuẩn WAV 44.1kHz."
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Đường dẫn file video/audio local HOẶC link YouTube (bỏ trống để chọn từ thư mục output/)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="source_20min.wav",
        help="Đường dẫn file WAV đầu ra (mặc định: source_20min.wav)",
    )
    parser.add_argument(
        "--start",
        default="00:03:00",
        help="Mốc bắt đầu cắt để bỏ intro (mặc định: 00:03:00)",
    )
    parser.add_argument(
        "--duration",
        default="00:20:00",
        help="Độ dài đoạn audio cần cắt (mặc định: 00:20:00 = 20 phút)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Tần số lấy mẫu đầu ra (mặc định: 44100 Hz cho Demucs & Seed-VC)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=2,
        choices=(1, 2),
        help="Số kênh âm thanh (mặc định: 2 stereo để Demucs tách vocal sạch nhất)",
    )
    parser.add_argument(
        "--lang",
        default="vi",
        help="Mã ngôn ngữ track âm thanh gốc muốn ưu tiên (mặc định: vi, tránh bản lồng tiếng tự động)",
    )
    parser.add_argument("--cookies", default=None, help="Đường dẫn file cookies.txt cho yt-dlp")
    parser.add_argument(
        "--cookies-from-browser",
        default=None,
        help="Lấy cookies từ trình duyệt (vd: chrome, firefox, edge)",
    )
    args = parser.parse_args()

    source = args.source
    if not source:
        videos = list_output_videos(Path("output"))
        if not videos:
            parser.error("Cần truyền đường dẫn file video/audio hoặc link YouTube.")
        print("Các video có sẵn trong thư mục output/:")
        for idx, v in enumerate(videos, start=1):
            dur = v.get("duration") or 0
            print(f"  [{idx}] ({dur // 60:02d}:{dur % 60:02d}) {v.get('title')} -> {v.get('url')}")
        choice = input("Chọn số thứ tự (Enter = 1): ").strip() or "1"
        if not choice.isdigit() or not (1 <= int(choice) <= len(videos)):
            print("Lựa chọn không hợp lệ.", file=sys.stderr)
            return 1
        source = videos[int(choice) - 1]["url"]

    start_sec = parse_hms_to_seconds(args.start)
    duration_sec = parse_hms_to_seconds(args.duration)
    output_wav = Path(args.output).resolve()

    if is_url(source):
        download_and_cut_url(
            url=source,
            output_wav=output_wav,
            start_sec=start_sec,
            duration_sec=duration_sec,
            sample_rate=args.sample_rate,
            channels=args.channels,
            lang=args.lang,
            cookies=args.cookies,
            cookies_from_browser=args.cookies_from_browser,
        )
    else:
        src_path = Path(source).expanduser().resolve()
        if not src_path.exists():
            print(f"Không tìm thấy file: {src_path}", file=sys.stderr)
            return 1
        print(f"Đang trích xuất & cắt {args.duration} từ mốc {args.start} -> {output_wav}")
        cut_with_ffmpeg(
            input_path=src_path,
            output_wav=output_wav,
            start_sec=start_sec,
            duration_sec=duration_sec,
            sample_rate=args.sample_rate,
            channels=args.channels,
            skip_seek=False,
        )

    actual_dur = probe_duration(output_wav)
    size_mb = output_wav.stat().st_size / (1024 * 1024)
    dur_str = f"{actual_dur / 60:.2f} phút" if actual_dur is not None else "không xác định"
    print(f"Hoàn tất! File: {output_wav} | Thời lượng: {dur_str} | Dung lượng: {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
