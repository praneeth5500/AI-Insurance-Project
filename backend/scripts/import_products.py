"""Import manually verified product data.

    make import-products FILE=path/to/file.json

Validates the whole file before writing anything, and refuses any record
without complete provenance. See app/products/importer.py for the rules.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, get_session, init_engine
from app.products.importer import ImportError_, import_versions


def read_payload(path: Path) -> object | None:
    """Load the file. Synchronous on purpose — it runs before the event loop."""
    if not path.exists():
        print(f"No such file: {path}")
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"{path} is not valid JSON: {error}")
        return None

    # The template ships with a _README key; drop anything that is not data.
    if isinstance(payload, dict):
        return {key: value for key, value in payload.items() if not key.startswith("_")}
    return payload


async def main(payload: object) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)

    init_engine(settings)
    try:
        agen = get_session()
        db = await anext(agen)
        try:
            report = await import_versions(db, payload)
        finally:
            await agen.aclose()
    except ImportError_ as error:
        print("Import refused. Nothing was written.\n")
        print(str(error))
        return 1
    finally:
        await dispose_engine()

    print(f"Versions inserted: {report.inserted_versions}")
    print(f"Versions re-verified: {report.replaced_versions}")
    print(f"Facts written: {report.inserted_facts}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: make import-products FILE=path/to/file.json")
        raise SystemExit(1)
    contents = read_payload(Path(sys.argv[1]))
    if contents is None:
        raise SystemExit(1)
    raise SystemExit(asyncio.run(main(contents)))
