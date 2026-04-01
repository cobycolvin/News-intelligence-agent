import json
from pathlib import Path
from typing import Any, List


class SampleDataRepository:
    def __init__(self, path: str):
        self.path = Path(path)

    def load_articles(self) -> List[dict[str, Any]]:
        if not self.path.exists():
            raise FileNotFoundError(f"Sample data not found at {self.path}")
        return json.loads(self.path.read_text(encoding="utf-8"))
