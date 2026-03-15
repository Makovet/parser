from __future__ import annotations

from pathlib import Path
import yaml

from qms_doc_parser.models.registry_models import StyleRegistryConfig


def load_style_registry(path: str | Path) -> StyleRegistryConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Style registry file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return StyleRegistryConfig.model_validate(data)