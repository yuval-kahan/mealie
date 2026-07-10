from pathlib import Path
from unittest.mock import AsyncMock

import mealie.services.recipe.video_asset_service as video_module
import pytest
from mealie.services.recipe.video_asset_service import VideoTranscodeError, normalize_video_asset


@pytest.mark.asyncio
async def test_browser_compatible_mp4_is_not_transcoded(tmp_path, monkeypatch):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")
    monkeypatch.setattr(video_module, "_is_browser_compatible_mp4", AsyncMock(return_value=True))

    result = await normalize_video_asset(source)

    assert result == source
    assert source.read_bytes() == b"video"


@pytest.mark.asyncio
async def test_non_mp4_is_transcoded_and_source_removed(tmp_path, monkeypatch):
    source = tmp_path / "clip.mkv"
    source.write_bytes(b"source")
    monkeypatch.setattr(video_module, "_is_browser_compatible_mp4", AsyncMock(return_value=False))
    monkeypatch.setattr(video_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    async def fake_process(*args: str, timeout: float):
        Path(args[-1]).write_bytes(b"converted")
        return 0, b"", b""

    monkeypatch.setattr(video_module, "_run_process", fake_process)

    result = await normalize_video_asset(source)

    assert result == tmp_path / "clip.mp4"
    assert result.read_bytes() == b"converted"
    assert not source.exists()


@pytest.mark.asyncio
async def test_transcode_failure_cleans_partial_output(tmp_path, monkeypatch):
    source = tmp_path / "clip.avi"
    source.write_bytes(b"source")
    monkeypatch.setattr(video_module, "_is_browser_compatible_mp4", AsyncMock(return_value=False))
    monkeypatch.setattr(video_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    async def fake_process(*args: str, timeout: float):
        Path(args[-1]).write_bytes(b"partial")
        return 1, b"", b"invalid video"

    monkeypatch.setattr(video_module, "_run_process", fake_process)

    with pytest.raises(VideoTranscodeError, match="invalid video"):
        await normalize_video_asset(source)

    assert source.exists()
    assert not (tmp_path / "clip.mp4").exists()


@pytest.mark.asyncio
async def test_transcode_does_not_overwrite_an_existing_mp4(tmp_path, monkeypatch):
    source = tmp_path / "clip.avi"
    existing = tmp_path / "clip.mp4"
    source.write_bytes(b"source")
    existing.write_bytes(b"keep-me")
    monkeypatch.setattr(video_module, "_is_browser_compatible_mp4", AsyncMock(return_value=False))

    with pytest.raises(VideoTranscodeError, match="already exists"):
        await normalize_video_asset(source)

    assert source.read_bytes() == b"source"
    assert existing.read_bytes() == b"keep-me"
