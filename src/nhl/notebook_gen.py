from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List

import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

from nhl.fetcher import fetch_endpoint
from nhl.analyzer import FieldInfo, analyze_response, suggest_model


def _table_name_from_url(url: str) -> str:
    path = url.split("?")[0].rstrip("/")
    last_seg = path.rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "_", last_seg.lower()).strip("_") or "nhl_data"


def _field_table_md(fields: List[FieldInfo]) -> str:
    rows = ["| Field | Type | Sample Value |", "|-------|------|--------------|"]
    for f in fields:
        sample = str(f.sample_value)[:60]
        rows.append(f"| `{f.name}` | `{f.python_type}` | `{sample}` |")
    return "\n".join(rows)


def generate_notebook(url: str, output_path: "str | Path") -> None:
    data = fetch_endpoint(url)
    fields = analyze_response(data)
    table_name = _table_name_from_url(url)
    model_code = suggest_model(fields, table_name)

    nb = new_notebook()
    nb.cells = [
        new_markdown_cell(f"# NHL API Exploration\n\n**Endpoint:** `{url}`"),
        new_markdown_cell("## Raw JSON Response"),
        new_code_cell(f"data = {json.dumps(data, indent=2)}\ndata"),
        new_markdown_cell("## Field Analysis\n\n" + _field_table_md(fields)),
        new_markdown_cell("## Suggested SQLAlchemy Model"),
        new_code_cell(model_code),
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        nbformat.write(nb, f)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: nhl-explore <url> [output.ipynb]")
        sys.exit(1)
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "exploration.ipynb"
    generate_notebook(url, out)
    print(f"Notebook written to {out}")
