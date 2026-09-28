"""Run with: python scripts/generate_openapi.py

Doesn't need a live DB/Redis: it only introspects routes, never resolves a
container provider.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402


def main() -> None:
    schema = app.openapi()
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openapi.json")
    with open(out_path, "w") as f:
        json.dump(schema, f, indent=2)
        f.write("\n")
    print(f"Wrote OpenAPI schema to {out_path}")


if __name__ == "__main__":
    main()
