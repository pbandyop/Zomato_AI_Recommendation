from pathlib import Path

from src.phase0.bootstrap import ensure_directory


def test_ensure_directory_creates_path(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "path"
    ensure_directory(target)
    assert target.exists()
    assert target.is_dir()
