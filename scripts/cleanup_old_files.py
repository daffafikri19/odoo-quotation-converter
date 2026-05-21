"""Delete generated upload/export files older than the retention window.

This script is intentionally standalone so it can be run by cron, Windows Task
Scheduler, Docker cron jobs, or any other external scheduler without tying the
cleanup lifecycle to Flask workers.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RETENTION_DAYS = 3
DEFAULT_TARGET_DIRS = (
    PROJECT_ROOT / 'exports',
    PROJECT_ROOT / 'uploads',
)


@dataclass
class CleanupSummary:
    scanned_count: int = 0
    deleted_count: int = 0
    skipped_count: int = 0
    error_count: int = 0


def resolve_target_dirs(raw_paths: list[str] | None) -> list[Path]:
    """Resolve cleanup targets and keep them inside the project workspace."""
    if not raw_paths:
        return [path.resolve() for path in DEFAULT_TARGET_DIRS]

    target_dirs = []
    project_root = PROJECT_ROOT.resolve()

    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path

        resolved_path = path.resolve()
        if not resolved_path.is_relative_to(project_root):
            raise ValueError(f"Cleanup path must stay inside the project: {resolved_path}")

        target_dirs.append(resolved_path)

    return target_dirs


def is_safe_child(path: Path, target_dirs: list[Path]) -> bool:
    """Check that the file belongs to one of the cleanup target directories."""
    resolved_path = path.resolve()
    return any(resolved_path.is_relative_to(target_dir) for target_dir in target_dirs)


def iter_old_files(target_dirs: list[Path], cutoff: datetime):
    """Yield old files from target directories."""
    for target_dir in target_dirs:
        if not target_dir.exists():
            continue

        if not target_dir.is_dir():
            continue

        for path in target_dir.rglob('*'):
            if not path.is_file():
                continue

            try:
                modified_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            except FileNotFoundError:
                continue

            if modified_at < cutoff:
                yield path


def cleanup_old_files(days: int, target_dirs: list[Path], dry_run: bool = False) -> CleanupSummary:
    """Delete files older than `days` from the configured target directories."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    summary = CleanupSummary()

    for path in iter_old_files(target_dirs, cutoff):
        summary.scanned_count += 1

        if not is_safe_child(path, target_dirs):
            summary.skipped_count += 1
            print(f"SKIP unsafe path: {path}")
            continue

        if dry_run:
            summary.skipped_count += 1
            print(f"DRY RUN delete: {path}")
            continue

        try:
            path.unlink()
            summary.deleted_count += 1
            print(f"Deleted: {path}")
        except OSError as exc:
            summary.error_count += 1
            print(f"ERROR deleting {path}: {exc}")

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Delete generated files older than the retention window.'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help='Retention window in days. Default: 3.',
    )
    parser.add_argument(
        '--path',
        action='append',
        dest='paths',
        help='Relative or absolute project path to clean. Can be used multiple times.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show files that would be deleted without deleting them.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days < 1:
        print('--days must be at least 1')
        return 2

    try:
        target_dirs = resolve_target_dirs(args.paths)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    summary = cleanup_old_files(
        days=args.days,
        target_dirs=target_dirs,
        dry_run=args.dry_run,
    )
    print(
        'Cleanup summary: '
        f"scanned={summary.scanned_count}, "
        f"deleted={summary.deleted_count}, "
        f"skipped={summary.skipped_count}, "
        f"errors={summary.error_count}"
    )

    return 1 if summary.error_count else 0


if __name__ == '__main__':
    raise SystemExit(main())
