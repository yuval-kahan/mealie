import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mealie.core import root_logger
from mealie.core.config import get_app_dirs, get_app_settings
from mealie.services.backups_v2.backup_v2 import BackupV2

logger = root_logger.get_logger()
_backup_lock = threading.Lock()


def _created_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def create_automatic_backup() -> None:
    settings = get_app_settings()
    if not settings.AUTO_BACKUP_ENABLED:
        return

    if not _backup_lock.acquire(blocking=False):
        logger.info("Skipping automatic backup because another backup is already running")
        return

    try:
        backup_dir = get_app_dirs().BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        backups = sorted(
            (path for path in backup_dir.glob("automatic_*.zip") if path.is_file()),
            key=_created_at,
            reverse=True,
        )
        minimum_age = timedelta(hours=settings.AUTO_BACKUP_INTERVAL_HOURS)
        if backups and datetime.now(UTC) - _created_at(backups[0]) < minimum_age:
            return

        created = BackupV2().backup(name_prefix="automatic")
        logger.info("Automatic backup created at %s", created)

        backups = sorted(
            (path for path in backup_dir.glob("automatic_*.zip") if path.is_file()),
            key=_created_at,
            reverse=True,
        )
        for stale_backup in backups[settings.AUTO_BACKUP_KEEP :]:
            try:
                stale_backup.unlink()
            except OSError as error:
                logger.warning("Could not remove old automatic backup %s: %s", stale_backup, error)
    finally:
        _backup_lock.release()
