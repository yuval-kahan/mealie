import asyncio
import shutil
from pathlib import Path

VIDEO_ASSET_EXTENSIONS = frozenset(
    {
        "3g2",
        "3gp",
        "amv",
        "asf",
        "avi",
        "divx",
        "dv",
        "f4v",
        "flv",
        "m1v",
        "m2ts",
        "m2v",
        "m4v",
        "mkv",
        "mod",
        "mov",
        "mp4",
        "mpe",
        "mpeg",
        "mpg",
        "mts",
        "mxf",
        "nut",
        "ogm",
        "ogv",
        "rm",
        "rmvb",
        "roq",
        "tod",
        "ts",
        "vob",
        "webm",
        "wmv",
        "y4m",
    }
)

VIDEO_MEDIA_TYPES = {
    ".3g2": "video/3gpp2",
    ".3gp": "video/3gpp",
    ".asf": "video/x-ms-asf",
    ".avi": "video/x-msvideo",
    ".f4v": "video/x-f4v",
    ".flv": "video/x-flv",
    ".m1v": "video/mpeg",
    ".m2ts": "video/mp2t",
    ".m2v": "video/mpeg",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
    ".mpe": "video/mpeg",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".mts": "video/mp2t",
    ".ogm": "video/ogg",
    ".ogv": "video/ogg",
    ".rm": "application/vnd.rn-realmedia",
    ".rmvb": "application/vnd.rn-realmedia-vbr",
    ".ts": "video/mp2t",
    ".vob": "video/mpeg",
    ".webm": "video/webm",
    ".wmv": "video/x-ms-wmv",
}


class VideoTranscodeError(RuntimeError):
    pass


async def _run_process(*args: str, timeout: float) -> tuple[int, bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise VideoTranscodeError("Video conversion timed out") from None
    return process.returncode or 0, stdout, stderr


async def _is_browser_compatible_mp4(path: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or path.suffix.lower() != ".mp4":
        return False

    code, stdout, _ = await _run_process(
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
        timeout=30,
    )
    return code == 0 and stdout.decode("utf-8", errors="ignore").strip().lower() in {"h264", "avc1"}


async def normalize_video_asset(path: Path, *, timeout: float = 7200) -> Path:
    """Return a browser-safe MP4, transcoding with FFmpeg only when needed."""

    if await _is_browser_compatible_mp4(path):
        return path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise VideoTranscodeError("FFmpeg is not installed")

    output_path = path.with_suffix(".mp4")
    replace_source = output_path == path
    if not replace_source and output_path.exists():
        raise VideoTranscodeError("A converted MP4 with this asset name already exists")

    working_output = path.with_name(f".{path.stem}.transcoding.mp4") if replace_source else output_path
    working_output.unlink(missing_ok=True)

    try:
        code, _, stderr = await _run_process(
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(working_output),
            timeout=timeout,
        )
        if code != 0 or not working_output.is_file() or working_output.stat().st_size == 0:
            detail = stderr.decode("utf-8", errors="ignore").strip()[-1200:]
            raise VideoTranscodeError(detail or "FFmpeg could not convert this video")

        if replace_source:
            working_output.replace(path)
            return path

        path.unlink(missing_ok=True)
        return output_path
    except Exception:
        working_output.unlink(missing_ok=True)
        raise
