import json
from pathlib import Path
import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_data_dirs(tmp_path: Path):
    raw = tmp_path / "data" / "raw"
    proc = tmp_path / "data" / "processed"
    raw.mkdir(parents=True, exist_ok=True)
    proc.mkdir(parents=True, exist_ok=True)
    return {"raw": raw, "processed": proc}


def write_json(p: Path, obj: dict) -> None:
    p.write_text(json.dumps(obj), encoding="utf-8")
