"""
Demo seed documents loader.
Reads from seed.yaml — edit that file to add/modify demo documents.
"""

import yaml
from pathlib import Path


def load_seed_documents(path: str = "seed.yaml") -> list[dict]:
    with open(Path(path), encoding="utf-8") as f:
        return yaml.safe_load(f)["documents"]


SEED_DOCUMENTS = load_seed_documents()
