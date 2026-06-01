from __future__ import annotations

import pytest
import nbformat

from nhl.fetcher import fetch_endpoint
from nhl.analyzer import analyze_response, suggest_model, FieldInfo
from nhl.notebook_gen import generate_notebook, _table_name_from_url, _field_table_md


SAMPLE_URL = "https://api.nhle.com/stats/rest/en/team"
SAMPLE_RESPONSE = {
    "data": [
        {"id": 1, "fullName": "New Jersey Devils", "triCode": "NJD", "leagueId": 133, "active": True},
        {"id": 2, "fullName": "New York Islanders", "triCode": "NYI", "leagueId": 133, "active": True},
    ],
    "total": 2,
}


# ── fetcher ───────────────────────────────────────────────────────────────────

def test_fetch_endpoint_returns_parsed_json(requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    result = fetch_endpoint(SAMPLE_URL)
    assert result == SAMPLE_RESPONSE


def test_fetch_endpoint_raises_on_http_error(requests_mock):
    requests_mock.get(SAMPLE_URL, status_code=404)
    with pytest.raises(Exception):
        fetch_endpoint(SAMPLE_URL)


# ── analyzer ──────────────────────────────────────────────────────────────────

def test_analyze_response_extracts_field_names_from_data_list():
    fields = analyze_response(SAMPLE_RESPONSE)
    names = [f.name for f in fields]
    assert "id" in names
    assert "fullName" in names
    assert "triCode" in names


def test_analyze_response_extracts_correct_python_types():
    fields = analyze_response(SAMPLE_RESPONSE)
    type_map = {f.name: f.python_type for f in fields}
    assert type_map["id"] == "int"
    assert type_map["fullName"] == "str"
    assert type_map["active"] == "bool"


def test_analyze_response_captures_sample_values():
    fields = analyze_response(SAMPLE_RESPONSE)
    sample_map = {f.name: f.sample_value for f in fields}
    assert sample_map["id"] == 1
    assert sample_map["fullName"] == "New Jersey Devils"


def test_analyze_response_handles_flat_list():
    data = [{"name": "foo", "value": 42}]
    fields = analyze_response(data)
    assert len(fields) == 2
    assert fields[0].name == "name"


def test_analyze_response_handles_flat_dict():
    data = {"name": "foo", "count": 10}
    fields = analyze_response(data)
    names = [f.name for f in fields]
    assert "name" in names
    assert "count" in names


def test_suggest_model_generates_class_and_tablename():
    fields = [FieldInfo(name="id", python_type="int", sample_value=1, nullable=False)]
    code = suggest_model(fields, "team")
    assert "class Team(Base):" in code
    assert '__tablename__ = "team"' in code


def test_suggest_model_maps_python_types_to_sqlalchemy():
    fields = [
        FieldInfo(name="id", python_type="int", sample_value=1, nullable=False),
        FieldInfo(name="name", python_type="str", sample_value="foo", nullable=False),
        FieldInfo(name="score", python_type="float", sample_value=1.5, nullable=False),
        FieldInfo(name="active", python_type="bool", sample_value=True, nullable=False),
    ]
    code = suggest_model(fields, "team")
    assert "Column(Integer" in code
    assert "Column(String" in code
    assert "Column(Float" in code
    assert "Column(Boolean" in code


def test_suggest_model_marks_id_as_primary_key():
    fields = [FieldInfo(name="id", python_type="int", sample_value=1, nullable=False)]
    code = suggest_model(fields, "team")
    assert "primary_key=True" in code


def test_suggest_model_adds_autoincrement_pk_when_no_id_field():
    fields = [FieldInfo(name="name", python_type="str", sample_value="foo", nullable=False)]
    code = suggest_model(fields, "team")
    assert "autoincrement=True" in code


# ── notebook_gen helpers ───────────────────────────────────────────────────────

def test_table_name_from_url_extracts_last_path_segment():
    assert _table_name_from_url("https://api.nhle.com/stats/rest/en/team") == "team"


def test_table_name_from_url_strips_query_string():
    assert _table_name_from_url("https://api.nhle.com/stats/rest/en/team?limit=10") == "team"


def test_field_table_md_produces_markdown_table_with_header():
    fields = [FieldInfo(name="id", python_type="int", sample_value=1, nullable=False)]
    md = _field_table_md(fields)
    assert "| Field |" in md
    assert "| `id` |" in md
    assert "| `int` |" in md
    assert "| `1` |" in md


# ── generate_notebook end-to-end ──────────────────────────────────────────────

def test_generate_notebook_creates_file(tmp_path, requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    out = tmp_path / "test.ipynb"
    generate_notebook(SAMPLE_URL, out)
    assert out.exists()


def test_generate_notebook_is_valid_nbformat4(tmp_path, requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    out = tmp_path / "test.ipynb"
    generate_notebook(SAMPLE_URL, out)
    nb = nbformat.read(str(out), as_version=4)
    assert nb.nbformat == 4
    assert len(nb.cells) > 0


def test_generate_notebook_contains_raw_json_cell(tmp_path, requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    out = tmp_path / "test.ipynb"
    generate_notebook(SAMPLE_URL, out)
    nb = nbformat.read(str(out), as_version=4)
    sources = [c.source for c in nb.cells]
    assert any("New Jersey Devils" in s for s in sources)


def test_generate_notebook_contains_field_breakdown(tmp_path, requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    out = tmp_path / "test.ipynb"
    generate_notebook(SAMPLE_URL, out)
    nb = nbformat.read(str(out), as_version=4)
    sources = [c.source for c in nb.cells]
    assert any("fullName" in s for s in sources)
    assert any("Field" in s and "Type" in s for s in sources)


def test_generate_notebook_contains_sqlalchemy_model(tmp_path, requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    out = tmp_path / "test.ipynb"
    generate_notebook(SAMPLE_URL, out)
    nb = nbformat.read(str(out), as_version=4)
    sources = [c.source for c in nb.cells]
    assert any("Column" in s for s in sources)
    assert any("class" in s and "Base" in s for s in sources)


def test_generate_notebook_url_appears_in_notebook(tmp_path, requests_mock):
    requests_mock.get(SAMPLE_URL, json=SAMPLE_RESPONSE)
    out = tmp_path / "test.ipynb"
    generate_notebook(SAMPLE_URL, out)
    nb = nbformat.read(str(out), as_version=4)
    sources = [c.source for c in nb.cells]
    assert any(SAMPLE_URL in s for s in sources)
