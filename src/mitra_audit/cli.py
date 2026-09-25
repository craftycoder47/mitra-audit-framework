"""Small CLI for running the sanitised audit against JSON evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import audit_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a fail-closed MITRA evidence audit")
    parser.add_argument("payload", type=Path, help="JSON evidence payload")
    args = parser.parse_args()

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    result = audit_payload(payload)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
