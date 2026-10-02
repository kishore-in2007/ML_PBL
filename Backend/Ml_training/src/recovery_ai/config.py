from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    raw: dict[str, Any]
    path: Path

    @property
    def classes(self) -> list[str]:
        return list(self.raw["data"]["classes"])


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig(raw=raw, path=config_path)
