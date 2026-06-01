from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Union


@dataclass
class FieldInfo:
    name: str
    python_type: str
    sample_value: Any
    nullable: bool


_SA_TYPE_MAP = {
    "str": "String",
    "int": "Integer",
    "float": "Float",
    "bool": "Boolean",
    "NoneType": "String",
}

_LIST_KEYS = ("data", "teams", "players", "games", "records", "items")


def _extract_records(data: Union[dict, list]) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in _LIST_KEYS:
            if key in data and isinstance(data[key], list):
                return data[key]
        return [data]
    return []


def analyze_response(data: Union[dict, list]) -> List[FieldInfo]:
    records = _extract_records(data)
    if not records or not isinstance(records[0], dict):
        return []
    first = records[0]
    return [
        FieldInfo(
            name=name,
            python_type=type(value).__name__,
            sample_value=value,
            nullable=value is None,
        )
        for name, value in first.items()
    ]


def suggest_model(fields: List[FieldInfo], table_name: str) -> str:
    class_name = table_name.replace("_", " ").title().replace(" ", "")
    lines = [
        "from sqlalchemy import Column, Integer, Float, String, Boolean",
        "from sqlalchemy.orm import DeclarativeBase",
        "",
        "",
        "class Base(DeclarativeBase):",
        "    pass",
        "",
        "",
        f"class {class_name}(Base):",
        f'    __tablename__ = "{table_name}"',
        "",
    ]

    has_id = any(f.name == "id" for f in fields)
    if not has_id:
        lines.append("    id = Column(Integer, primary_key=True, autoincrement=True)")

    for field in fields:
        sa_type = _SA_TYPE_MAP.get(field.python_type, "String")
        extras: list = []
        if field.name == "id":
            extras.append("primary_key=True")
        if field.nullable:
            extras.append("nullable=True")
        extras_str = ", ".join([""] + extras) if extras else ""
        lines.append(f"    {field.name} = Column({sa_type}{extras_str})")

    return "\n".join(lines)
