from plaitime.io import rename
from pathlib import Path


def test_rename(tmp_path):
    path: Path = tmp_path / "foo.txt"
    path.touch()

    rename(path, "bar")

    assert not path.exists()
    assert (tmp_path / "bar.txt").exists()
