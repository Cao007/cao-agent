import json
from pathlib import Path

from backend.app.main import create_api

if __name__ == "__main__":
    Path("docs/openapi.json").write_text(
        json.dumps(create_api().openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
