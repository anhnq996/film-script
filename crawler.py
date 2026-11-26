#!/usr/bin/env python3
"""
YouTube Channel Transcript Crawler (no YouTube Data API required).

Uses `yt-dlp` to scan a YouTube channel's playlists and remaining videos (`other`),
then extracts clean transcripts for every available language per video.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
MULTI_SPACE = re.compile(r"\s+")
VTT_TIMESTAMP_LINE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}"
)
XML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SubtitleTrack:
    lang: str
    name: str
    source: str  # "manual" | "auto" | "auto_translated"
    json3_url: str | None = None
    vtt_url: str | None = None


@dataclass
class VideoTranscriptBundle:
    video_id: str
    title: str
    url: str
    duration: int | None
    upload_date: str | None
    channel: str | None
    channel_id: str | None
    transcripts: dict[str, dict[str, Any]] = field(default_factory=dict)
    error: str | None = None


def sanitize_name(name: str, max_len: int = 90, fallback: str = "untitled") -> str:
    """Sanitize a string into a safe, readable directory/file name."""
    cleaned = INVALID_FILENAME_CHARS.sub(" ", name or "")
    cleaned = MULTI_SPACE.sub(" ", cleaned).strip(" .")
    if not cleaned:
        return fallback
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(" .")
    return cleaned or fallback


def make_video_folder_name(parent_dir: Path, v_idx: int, title: str, vid: str) -> str:
    """Build `{v_idx:03d} - <title> [<vid>]` respecting Windows MAX_PATH limits."""
    prefix = f"{v_idx:03d} - "
    suffix = f" [{vid}]"
    max_title_len = 80
    if os.name == "nt":
        # Keep directory path <= 240 chars so directory creation and files stay < 260
        budget = 240 - len(str(parent_dir)) - 1 - len(prefix) - len(suffix)
        max_title_len = max(10, min(80, budget))
    safe_title = sanitize_name(title, max_len=max_title_len, fallback=vid)
    return f"{prefix}{safe_title}{suffix}"


def ensure_yt_dlp() -> str:
    """Verify yt-dlp is installed and return its executable path."""
    path = shutil.which("yt-dlp")
    if not path:
        raise RuntimeError(
            "Không tìm thấy `yt-dlp` trong PATH. Hãy cài đặt: pip install -U yt-dlp"
        )
    return path


def normalize_channel_base_url(raw_url: str) -> str:
    """Strip trailing tab suffixes (/videos, /playlists, etc.) from a channel URL."""
    url = raw_url.strip()
    if not url:
        raise ValueError("URL kênh không được để trống.")
    if not url.startswith(("http://", "https://")):
        if url.startswith("@"):
            url = f"https://www.youtube.com/{url}"
        else:
            url = f"https://www.youtube.com/{url.lstrip('/')}"

    url = url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    tabs = (
        "/featured",
        "/videos",
        "/shorts",
        "/streams",
        "/playlists",
        "/community",
        "/posts",
        "/channels",
        "/about",
        "/releases",
        "/podcasts",
    )
    for tab in tabs:
        if url.lower().endswith(tab):
            url = url[: -len(tab)]
            break
    return url.rstrip("/")


def build_yt_dlp_auth_args(
    cookies_file: str | None, cookies_from_browser: str | None
) -> list[str]:
    args: list[str] = []
    if cookies_file:
        args.extend(["--cookies", cookies_file])
    if cookies_from_browser:
        args.extend(["--cookies-from-browser", cookies_from_browser])
    return args


def run_yt_dlp_json(
    url: str,
    flat: bool = True,
    limit: int | None = None,
    auth_args: list[str] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Run yt-dlp with -J and return parsed JSON (or None + stderr on failure)."""
    cmd = ["yt-dlp", "-J", "--skip-download", "--ignore-errors", "--no-warnings"]
    if flat:
        cmd.append("--flat-playlist")
    if limit and limit > 0:
        cmd.extend(["--playlist-end", str(limit)])
    if auth_args:
        cmd.extend(auth_args)
    cmd.append(url)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = proc.stdout.strip()
    if not stdout:
        return None, proc.stderr.strip()

    # yt-dlp -J outputs a single JSON object (even if some entries errored).
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line), proc.stderr.strip()
            except json.JSONDecodeError:
                continue
    return None, proc.stderr.strip()


def resolve_channel_identity(
    input_url: str, auth_args: list[str]
) -> tuple[str, str, str]:
    """
    Resolve canonical channel_id, channel_name, and canonical base channel URL.
    """
    base_url = normalize_channel_base_url(input_url)
    for probe in (f"{base_url}/videos", base_url, f"{base_url}/playlists"):
        data, err = run_yt_dlp_json(probe, flat=True, limit=1, auth_args=auth_args)
        if data and (data.get("channel_id") or data.get("uploader_id")):
            channel_id = data.get("channel_id") or data.get("id") or "unknown"
            channel_name = (
                data.get("channel")
                or data.get("uploader")
                or data.get("title")
                or channel_id
            )
            # Strip trailing " - Videos" / " - Playlists" if fallback used title
            for suffix in (" - Videos", " - Playlists", " - Shorts", " - Live"):
                if channel_name.endswith(suffix):
                    channel_name = channel_name[: -len(suffix)]
            canonical = data.get("channel_url") or base_url
            canonical = normalize_channel_base_url(canonical)
            return channel_id, channel_name, canonical

    raise RuntimeError(
        f"Không thể đọc thông tin kênh từ URL: {input_url}. "
        "Hãy kiểm tra lại link kênh hoặc kết nối mạng."
    )


def fetch_channel_playlists(
    canonical_base: str,
    playlist_limit: int | None,
    video_limit: int | None,
    auth_args: list[str],
) -> list[dict[str, Any]]:
    """Fetch all playlists from `<channel>/playlists` and their video entries."""
    data, _ = run_yt_dlp_json(
        f"{canonical_base}/playlists",
        flat=True,
        limit=playlist_limit,
        auth_args=auth_args,
    )
    if not data:
        return []

    raw_playlists = data.get("entries") or []
    playlists: list[dict[str, Any]] = []
    for pl in raw_playlists:
        if not pl:
            continue
        pl_id = pl.get("id")
        pl_url = pl.get("url") or (
            f"https://www.youtube.com/playlist?list={pl_id}" if pl_id else None
        )
        if not pl_url:
            continue
        pl_title = pl.get("title") or pl_id or "Playlist"
        pl_data, _ = run_yt_dlp_json(
            pl_url, flat=True, limit=video_limit, auth_args=auth_args
        )
        entries = normalize_video_entries((pl_data or {}).get("entries") or [])
        playlists.append(
            {
                "id": pl_id or "",
                "title": pl_title,
                "url": pl_url,
                "videos": entries,
            }
        )
    return playlists


def normalize_video_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter valid YouTube video entries from flat-playlist JSON."""
    videos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not entry:
            continue
        vid = entry.get("id")
        title = entry.get("title") or ""
        if not vid or title in ("[Private video]", "[Deleted video]"):
            continue
        # Skip non-video tab items if any appear
        if entry.get("_type") == "playlist":
            continue
        if vid in seen:
            continue
        seen.add(vid)
        videos.append(
            {
                "id": vid,
                "title": title or vid,
                "url": entry.get("url") or f"https://www.youtube.com/watch?v={vid}",
                "duration": entry.get("duration"),
            }
        )
    return videos


def fetch_channel_tab_videos(
    canonical_base: str,
    tabs: list[str],
    video_limit: int | None,
    auth_args: list[str],
) -> list[dict[str, Any]]:
    """Fetch videos from channel tabs (e.g., videos, shorts, streams)."""
    all_videos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tab in tabs:
        data, _ = run_yt_dlp_json(
            f"{canonical_base}/{tab}",
            flat=True,
            limit=video_limit,
            auth_args=auth_args,
        )
        if not data:
            continue
        for v in normalize_video_entries(data.get("entries") or []):
            if v["id"] in seen:
                continue
            seen.add(v["id"])
            v["tab"] = tab
            all_videos.append(v)
    return all_videos


def _extract_formats(formats: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    json3_url = None
    vtt_url = None
    for fmt in formats:
        ext = fmt.get("ext")
        if ext == "json3" and not json3_url:
            json3_url = fmt.get("url")
        elif ext == "vtt" and not vtt_url:
            vtt_url = fmt.get("url")
    return json3_url, vtt_url


def _base_lang(lang: str) -> str:
    return lang[:-5] if lang.endswith("-orig") else lang


def select_subtitle_tracks(
    video_json: dict[str, Any], requested_langs: list[str] | None
) -> list[SubtitleTrack]:
    """
    Pick subtitle tracks to download for a video.

    - When requested_langs is None ("auto" mode):
      Download ALL manual subtitles (excluding live_chat) + original auto-generated
      caption(s) (those without `tlang=` in URL) if not already covered by manual.
    - When requested_langs is provided (e.g. ["vi", "en"]):
      For each requested language, prefer manual -> original auto -> auto-translated.
    """
    manual_subs: dict[str, list[dict[str, Any]]] = {
        k: v
        for k, v in (video_json.get("subtitles") or {}).items()
        if k != "live_chat" and v
    }
    auto_subs: dict[str, list[dict[str, Any]]] = {
        k: v
        for k, v in (video_json.get("automatic_captions") or {}).items()
        if k != "live_chat" and v
    }

    # Identify original (non-translated) automatic captions
    orig_auto: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    for lang, fmts in auto_subs.items():
        if any("tlang=" in (f.get("url") or "") for f in fmts):
            continue
        base = _base_lang(lang)
        # Prefer `<lang>-orig` over `<lang>` if both appear, otherwise keep first
        if base not in orig_auto or lang.endswith("-orig"):
            orig_auto[base] = (lang, fmts)

    selected: dict[str, SubtitleTrack] = {}

    if not requested_langs:
        for lang, fmts in manual_subs.items():
            j3, vtt = _extract_formats(fmts)
            if j3 or vtt:
                selected[lang] = SubtitleTrack(
                    lang=lang,
                    name=fmts[0].get("name") or lang,
                    source="manual",
                    json3_url=j3,
                    vtt_url=vtt,
                )

        for base, (raw_lang, fmts) in orig_auto.items():
            if base in selected:
                continue
            j3, vtt = _extract_formats(fmts)
            if j3 or vtt:
                selected[base] = SubtitleTrack(
                    lang=base,
                    name=fmts[0].get("name") or raw_lang,
                    source="auto",
                    json3_url=j3,
                    vtt_url=vtt,
                )
        return list(selected.values())

    # Specific languages requested
    for req in requested_langs:
        req_clean = req.strip()
        if not req_clean:
            continue
        matched = False

        # 1. Manual exact or prefix match (e.g. "en" matches "en" or "en-US")
        for lang, fmts in manual_subs.items():
            if lang == req_clean or lang.startswith(f"{req_clean}-"):
                j3, vtt = _extract_formats(fmts)
                if j3 or vtt:
                    selected[lang] = SubtitleTrack(
                        lang=lang,
                        name=fmts[0].get("name") or lang,
                        source="manual",
                        json3_url=j3,
                        vtt_url=vtt,
                    )
                    matched = True
        if matched:
            continue

        # 2. Original auto match
        if req_clean in orig_auto:
            raw_lang, fmts = orig_auto[req_clean]
            j3, vtt = _extract_formats(fmts)
            if j3 or vtt:
                selected[req_clean] = SubtitleTrack(
                    lang=req_clean,
                    name=fmts[0].get("name") or raw_lang,
                    source="auto",
                    json3_url=j3,
                    vtt_url=vtt,
                )
                continue

        # 3. Auto-translated fallback
        if req_clean in auto_subs:
            fmts = auto_subs[req_clean]
            j3, vtt = _extract_formats(fmts)
            if j3 or vtt:
                selected[req_clean] = SubtitleTrack(
                    lang=req_clean,
                    name=fmts[0].get("name") or req_clean,
                    source="auto_translated",
                    json3_url=j3,
                    vtt_url=vtt,
                )

    return list(selected.values())


def http_get_text(url: str, retries: int = 5) -> str:
    """Download text from a URL with retry & exponential backoff on 429/5xx."""
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(min(20, 2 ** (attempt + 1)))
                continue
            raise
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    assert last_err is not None
    raise last_err


def format_timestamp(ms: int) -> str:
    total_sec = max(0, ms // 1000)
    hours, rem = divmod(total_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_srt_timestamp(ms: int) -> str:
    ms = max(0, ms)
    total_sec, rem_ms = divmod(ms, 1000)
    hours, rem = divmod(total_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{rem_ms:03d}"


def parse_json3_cues(raw_json: str) -> list[tuple[int, int, str]]:
    """Parse YouTube json3 subtitle payload into [(start_ms, end_ms, text)]."""
    data = json.loads(raw_json)
    cues: list[tuple[int, int, str]] = []
    for ev in data.get("events") or []:
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs)
        text = html.unescape(text)
        text = MULTI_SPACE.sub(" ", text).strip()
        if not text:
            continue
        start_ms = int(ev.get("tStartMs", 0))
        dur_ms = int(ev.get("dDurationMs", 2000))
        cues.append((start_ms, start_ms + dur_ms, text))
    return cues


def _parse_vtt_ms(ts: str) -> int:
    ts = ts.replace(",", ".").strip()
    parts = ts.split(":")
    if len(parts) == 2:
        m, s = parts
        h = "0"
    elif len(parts) == 3:
        h, m, s = parts
    else:
        return 0
    sec_parts = s.split(".")
    sec = int(sec_parts[0])
    ms = int(sec_parts[1].ljust(3, "0")[:3]) if len(sec_parts) > 1 else 0
    return ((int(h) * 3600) + (int(m) * 60) + sec) * 1000 + ms


def parse_vtt_cues(raw_vtt: str) -> list[tuple[int, int, str]]:
    """Parse WebVTT payload into deduplicated [(start_ms, end_ms, text)]."""
    cues: list[tuple[int, int, str]] = []
    lines = raw_vtt.splitlines()
    i = 0
    last_text = ""
    while i < len(lines):
        line = lines[i].strip()
        if VTT_TIMESTAMP_LINE.match(line):
            times = line.split("-->")
            start_ms = _parse_vtt_ms(times[0])
            end_part = times[1].strip().split(" ")[0]
            end_ms = _parse_vtt_ms(end_part)
            i += 1
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                cleaned = XML_TAG_RE.sub("", lines[i])
                cleaned = html.unescape(cleaned).strip()
                if cleaned:
                    text_lines.append(cleaned)
                i += 1
            text = MULTI_SPACE.sub(" ", " ".join(text_lines)).strip()
            if text and text != last_text:
                cues.append((start_ms, end_ms, text))
                last_text = text
        else:
            i += 1
    return cues


def cues_to_txt(cues: list[tuple[int, int, str]], with_timestamps: bool) -> str:
    if with_timestamps:
        return "\n".join(f"[{format_timestamp(s)}] {t}" for s, _, t in cues) + "\n"
    return "\n".join(t for _, _, t in cues) + "\n"


def cues_to_srt(cues: list[tuple[int, int, str]]) -> str:
    blocks: list[str] = []
    for idx, (start_ms, end_ms, text) in enumerate(cues, start=1):
        blocks.append(
            f"{idx}\n{format_srt_timestamp(start_ms)} --> {format_srt_timestamp(end_ms)}\n{text}"
        )
    return "\n\n".join(blocks) + "\n"


def download_video_transcripts(
    video_entry: dict[str, Any],
    requested_langs: list[str] | None,
    with_timestamps: bool,
    save_srt: bool,
    auth_args: list[str],
) -> VideoTranscriptBundle:
    """Extract metadata and all available transcripts for a single video."""
    vid = video_entry["id"]
    url = video_entry["url"]
    data, err = run_yt_dlp_json(url, flat=False, auth_args=auth_args)
    if not data:
        return VideoTranscriptBundle(
            video_id=vid,
            title=video_entry.get("title") or vid,
            url=url,
            duration=video_entry.get("duration"),
            upload_date=None,
            channel=None,
            channel_id=None,
            error=err or "Không thể lấy metadata video",
        )

    bundle = VideoTranscriptBundle(
        video_id=vid,
        title=data.get("title") or video_entry.get("title") or vid,
        url=data.get("webpage_url") or url,
        duration=data.get("duration"),
        upload_date=data.get("upload_date"),
        channel=data.get("channel"),
        channel_id=data.get("channel_id"),
    )

    tracks = select_subtitle_tracks(data, requested_langs)
    for track in tracks:
        cues: list[tuple[int, int, str]] = []
        try:
            if track.json3_url:
                raw = http_get_text(track.json3_url)
                cues = parse_json3_cues(raw)
            elif track.vtt_url:
                raw = http_get_text(track.vtt_url)
                cues = parse_vtt_cues(raw)
        except Exception as exc:
            bundle.transcripts[track.lang] = {
                "name": track.name,
                "source": track.source,
                "error": str(exc),
            }
            continue

        if not cues:
            continue

        entry_data: dict[str, Any] = {
            "name": track.name,
            "source": track.source,
            "cue_count": len(cues),
            "txt": cues_to_txt(cues, with_timestamps=with_timestamps),
        }
        if save_srt:
            entry_data["srt"] = cues_to_srt(cues)
        bundle.transcripts[track.lang] = entry_data

    return bundle


def write_video_folder(
    target_dir: Path,
    bundle: VideoTranscriptBundle,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """Write video info.json and all language transcript files into target_dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    lang_summary: dict[str, Any] = {}

    for lang, tdata in bundle.transcripts.items():
        safe_lang = sanitize_name(lang, max_len=24, fallback="und")
        if "txt" in tdata:
            (target_dir / f"{safe_lang}.txt").write_text(
                tdata["txt"], encoding="utf-8"
            )
            if "srt" in tdata:
                (target_dir / f"{safe_lang}.srt").write_text(
                    tdata["srt"], encoding="utf-8"
                )
            lang_summary[lang] = {
                "name": tdata["name"],
                "source": tdata["source"],
                "cue_count": tdata["cue_count"],
                "file": f"{safe_lang}.txt",
            }
        else:
            lang_summary[lang] = {
                "name": tdata.get("name", lang),
                "source": tdata.get("source", "unknown"),
                "error": tdata.get("error", "empty"),
            }

    info = {
        "video_id": bundle.video_id,
        "title": bundle.title,
        "url": bundle.url,
        "duration": bundle.duration,
        "upload_date": bundle.upload_date,
        "channel": bundle.channel,
        "channel_id": bundle.channel_id,
        "has_transcript": any("file" in v for v in lang_summary.values()),
        "languages": lang_summary,
        "error": bundle.error,
        **(extra_meta or {}),
    }
    (target_dir / "info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_cached_bundle_from_disk(video_dir: Path) -> VideoTranscriptBundle | None:
    """Load an already-downloaded video directory into a VideoTranscriptBundle."""
    info_path = video_dir / "info.json"
    if not info_path.exists():
        return None
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if info.get("error"):
        return None
    if not info.get("has_transcript") and any(
        isinstance(v, dict) and "error" in v
        for v in (info.get("languages") or {}).values()
    ):
        return None

    bundle = VideoTranscriptBundle(
        video_id=info.get("video_id", ""),
        title=info.get("title", ""),
        url=info.get("url", ""),
        duration=info.get("duration"),
        upload_date=info.get("upload_date"),
        channel=info.get("channel"),
        channel_id=info.get("channel_id"),
    )
    for lang, meta in (info.get("languages") or {}).items():
        fname = meta.get("file")
        if not fname:
            continue
        txt_path = video_dir / fname
        if not txt_path.exists():
            continue
        entry: dict[str, Any] = {
            "name": meta.get("name", lang),
            "source": meta.get("source", "unknown"),
            "cue_count": meta.get("cue_count", 0),
            "txt": txt_path.read_text(encoding="utf-8"),
        }
        srt_path = video_dir / f"{Path(fname).stem}.srt"
        if srt_path.exists():
            entry["srt"] = srt_path.read_text(encoding="utf-8")
        bundle.transcripts[lang] = entry
    return bundle


def index_existing_videos(channel_dir: Path) -> dict[str, Path]:
    """Find previously downloaded video folders by `[video_id]` inside channel_dir."""
    existing: dict[str, Path] = {}
    if not channel_dir.exists():
        return existing
    id_re = re.compile(r"\[([A-Za-z0-9_-]{6,})\]$")
    for info_file in channel_dir.rglob("info.json"):
        vdir = info_file.parent
        m = id_re.search(vdir.name)
        if m:
            existing[m.group(1)] = vdir
    return existing


def prompt_if_interactive(args: argparse.Namespace) -> argparse.Namespace:
    """When run without a URL argument, prompt interactively with helpful defaults."""
    if args.url:
        return args

    print("=== YouTube Channel Transcript Crawler (No API) ===")
    while not args.url:
        args.url = input("Nhập link kênh YouTube (vd: https://www.youtube.com/@tenkenh): ").strip()

    langs_in = input(
        "Ngôn ngữ muốn lấy (vd: vi,en | Enter = tự động lấy toàn bộ phụ đề gốc/manual): "
    ).strip()
    if langs_in:
        args.langs = langs_in

    shorts_in = input("Quét thêm Shorts vào mục other/? [y/N]: ").strip().lower()
    if shorts_in in ("y", "yes", "1"):
        args.include_shorts = True

    ts_in = input("Giữ mốc thời gian [MM:SS] trong file .txt? [y/N]: ").strip().lower()
    if ts_in in ("y", "yes", "1"):
        args.timestamps = True

    limit_in = input("Giới hạn số video mỗi playlist/tab (Enter = không giới hạn): ").strip()
    if limit_in.isdigit() and int(limit_in) > 0:
        args.limit = int(limit_in)

    return args


def crawl_channel(args: argparse.Namespace) -> Path:
    ensure_yt_dlp()

    auth_args = build_yt_dlp_auth_args(args.cookies, args.cookies_from_browser)
    requested_langs = (
        [x.strip() for x in args.langs.split(",") if x.strip()]
        if args.langs and args.langs.lower() != "auto"
        else None
    )

    print(f"[1/4] Đang nhận diện kênh từ: {args.url}")
    channel_id, channel_name, canonical_base = resolve_channel_identity(
        args.url, auth_args
    )
    channel_dir_name = f"{sanitize_name(channel_name, max_len=70)} [{channel_id}]"
    channel_dir = Path(args.output).resolve() / channel_dir_name
    playlists_root = channel_dir / "playlists"
    other_root = channel_dir / "other"
    channel_dir.mkdir(parents=True, exist_ok=True)
    playlists_root.mkdir(parents=True, exist_ok=True)
    other_root.mkdir(parents=True, exist_ok=True)

    print(f"      Kênh: {channel_name} ({channel_id})")
    print(f"      Thư mục xuất: {channel_dir}")

    print("[2/4] Đang quét danh sách playlists...")
    playlists = fetch_channel_playlists(
        canonical_base,
        playlist_limit=args.playlist_limit,
        video_limit=args.limit,
        auth_args=auth_args,
    )
    playlist_video_ids: set[str] = set()
    for pl in playlists:
        for v in pl["videos"]:
            playlist_video_ids.add(v["id"])
    print(f"      Tìm thấy {len(playlists)} playlist ({len(playlist_video_ids)} video unique).")

    if args.playlists_only:
        print("[3/4] Bỏ qua quét video ngoài playlist (--playlists-only).")
        other_videos: list[dict[str, Any]] = []
    else:
        tabs = ["videos"]
        if args.include_shorts:
            tabs.append("shorts")
        if args.include_streams:
            tabs.append("streams")

        print(f"[3/4] Đang quét các video ngoài playlist ({', '.join(tabs)})...")
        tab_videos = fetch_channel_tab_videos(
            canonical_base, tabs=tabs, video_limit=args.limit, auth_args=auth_args
        )
        other_videos = [v for v in tab_videos if v["id"] not in playlist_video_ids]
        print(
            f"      Tổng video trên tab: {len(tab_videos)} | "
            f"Thuộc mục other/: {len(other_videos)}"
        )

    existing_dirs = {} if args.force else index_existing_videos(channel_dir)
    cache: dict[str, VideoTranscriptBundle] = {}

    print("[4/4] Đang tải và xuất transcript...")
    used_playlist_names: set[str] = set()
    playlist_summary: list[dict[str, Any]] = []
    placements_by_vid: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    unique_videos: dict[str, dict[str, Any]] = {}

    for pl_idx, pl in enumerate(playlists, start=1):
        base_pl_name = sanitize_name(pl["title"], max_len=80, fallback=f"playlist_{pl_idx}")
        pl_folder_name = base_pl_name
        if pl_folder_name.lower() in used_playlist_names:
            pl_id_suffix = f" [{pl['id']}]"
            if os.name == "nt":
                short_base = sanitize_name(
                    pl["title"],
                    max_len=max(20, 72 - len(pl_id_suffix)),
                    fallback=f"playlist_{pl_idx}",
                )
                pl_folder_name = f"{short_base}{pl_id_suffix}"
            else:
                pl_folder_name = f"{base_pl_name}{pl_id_suffix}"
        used_playlist_names.add(pl_folder_name.lower())

        pl_dir = playlists_root / pl_folder_name
        pl_dir.mkdir(parents=True, exist_ok=True)
        (pl_dir / "_playlist.json").write_text(
            json.dumps(
                {
                    "playlist_id": pl["id"],
                    "title": pl["title"],
                    "url": pl["url"],
                    "video_count": len(pl["videos"]),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        for v_idx, video in enumerate(pl["videos"], start=1):
            vid = video["id"]
            v_folder = make_video_folder_name(pl_dir, v_idx, video["title"], vid)
            unique_videos.setdefault(vid, video)
            placements_by_vid.setdefault(vid, []).append(
                (pl_dir / v_folder, {"playlist": pl["title"], "playlist_id": pl["id"]})
            )

        playlist_summary.append(
            {
                "id": pl["id"],
                "title": pl["title"],
                "folder": f"playlists/{pl_folder_name}",
                "video_count": len(pl["videos"]),
            }
        )

    for v_idx, video in enumerate(other_videos, start=1):
        vid = video["id"]
        v_folder = make_video_folder_name(other_root, v_idx, video["title"], vid)
        unique_videos.setdefault(vid, video)
        placements_by_vid.setdefault(vid, []).append(
            (other_root / v_folder, {"playlist": None, "tab": video.get("tab", "videos")})
        )

    skipped_count = 0
    to_fetch: list[dict[str, Any]] = []
    for vid, video in unique_videos.items():
        if not args.force and vid in existing_dirs:
            cached_disk = load_cached_bundle_from_disk(existing_dirs[vid])
            if cached_disk is not None:
                cache[vid] = cached_disk
                for target_dir, extra_meta in placements_by_vid[vid]:
                    write_video_folder(target_dir, cached_disk, extra_meta=extra_meta)
                skipped_count += 1
                continue
        to_fetch.append(video)

    workers = max(1, args.workers)
    total_to_fetch = len(to_fetch)
    print(
        f"      Tổng video unique: {len(unique_videos)} | "
        f"Bỏ qua đã có: {skipped_count} | "
        f"Cần tải: {total_to_fetch} (workers={workers})"
    )

    cache_lock = threading.Lock()
    done_count = 0

    def fetch_and_persist(video_entry: dict[str, Any]) -> None:
        nonlocal done_count
        vid = video_entry["id"]
        bundle = download_video_transcripts(
            video_entry=video_entry,
            requested_langs=requested_langs,
            with_timestamps=args.timestamps,
            save_srt=args.srt,
            auth_args=auth_args,
        )
        for target_dir, extra_meta in placements_by_vid[vid]:
            write_video_folder(target_dir, bundle, extra_meta=extra_meta)

        has_txt = any("txt" in t for t in bundle.transcripts.values())
        status = "ok" if has_txt else ("err" if bundle.error else "no-sub")
        with cache_lock:
            cache[vid] = bundle
            done_count += 1
            current = done_count
            print(
                f"      [{current}/{total_to_fetch}] [{status}] "
                f"{video_entry['title'][:60]} ({vid})",
                flush=True,
            )

        if args.sleep > 0:
            time.sleep(args.sleep)

    if total_to_fetch > 0:
        if workers == 1:
            for video in to_fetch:
                fetch_and_persist(video)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(fetch_and_persist, video) for video in to_fetch]
                for fut in concurrent.futures.as_completed(futures):
                    fut.result()

    channel_info = {
        "channel": channel_name,
        "channel_id": channel_id,
        "input_url": args.url,
        "canonical_url": canonical_base,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "requested_langs": requested_langs or "auto",
        "playlists": playlist_summary,
        "other_video_count": len(other_videos),
        "unique_videos_processed": len(cache),
    }
    (channel_dir / "channel_info.json").write_text(
        json.dumps(channel_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nHoàn tất!")
    print(f"Kết quả lưu tại: {channel_dir}")
    return channel_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quét kênh YouTube (không dùng API) và xuất transcript theo playlist / other."
    )
    parser.add_argument("url", nargs="?", help="Link kênh YouTube")
    parser.add_argument(
        "-o",
        "--output",
        default=str(Path(__file__).resolve().parent / "output"),
        help="Thư mục gốc lưu kết quả (mặc định: ./output)",
    )
    parser.add_argument(
        "--langs",
        default="auto",
        help="Các ngôn ngữ muốn lấy, cách nhau bởi dấu phẩy (vd: vi,en). Mặc định: auto (toàn bộ phụ đề manual + auto gốc)",
    )
    parser.add_argument(
        "--include-shorts",
        action="store_true",
        help="Quét thêm tab /shorts đưa vào other/",
    )
    parser.add_argument(
        "--include-streams",
        action="store_true",
        help="Quét thêm tab /streams đưa vào other/",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số video tối đa cho mỗi playlist và mỗi tab",
    )
    parser.add_argument(
        "--playlist-limit",
        type=int,
        default=None,
        help="Giới hạn số playlist tối đa của kênh",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Thời gian nghỉ (giây) giữa mỗi video để tránh rate-limit (mặc định: 1.0)",
    )
    parser.add_argument(
        "--timestamps",
        action="store_true",
        help="Thêm mốc thời gian [MM:SS] vào đầu mỗi dòng trong file .txt",
    )
    parser.add_argument(
        "--srt",
        action="store_true",
        help="Xuất thêm file phụ đề .srt bên cạnh .txt",
    )
    parser.add_argument(
        "--playlists-only",
        action="store_true",
        help="Chỉ quét các playlists, bỏ qua bước quét video ngoài playlist (other/)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Số luồng tải đồng thời khi lấy transcript (mặc định: 1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Tải lại kể cả các video đã có sẵn trong thư mục kênh",
    )
    parser.add_argument("--cookies", help="Đường dẫn tới file cookies.txt (Netscape format)")
    parser.add_argument(
        "--cookies-from-browser",
        help="Đọc cookies từ trình duyệt (vd: chrome, firefox) nếu YouTube yêu cầu đăng nhập",
    )
    return parser.parse_args(argv)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    try:
        args = parse_args()
        args = prompt_if_interactive(args)
        crawl_channel(args)
        return 0
    except KeyboardInterrupt:
        print("\nĐã dừng theo yêu cầu người dùng.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
