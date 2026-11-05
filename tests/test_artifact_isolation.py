"""Verify the safety boundary around legacy relative artifact paths."""

from pathlib import Path


def test_artifact_writes_are_temporary(tmp_path):
    assert Path.cwd() == tmp_path
    for folder in ("models", "reports"):
        target = Path(folder) / "1" / "test.txt"
        target.parent.mkdir()
        target.write_text("test output", encoding="utf-8")
        assert target.resolve().is_relative_to(tmp_path)
    assert Path("tests/data/kaggle_restaurant_sales.csv").is_file()
