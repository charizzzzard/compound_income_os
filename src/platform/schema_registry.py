"""Versioned CSV schema registry. Stdlib-only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    name: str
    required: bool = True
    enum: tuple[str, ...] | None = None
    numeric_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class Schema:
    name: str
    version: str
    fields: tuple[FieldSpec, ...]


class SchemaRegistry:
    def __init__(self) -> None:
        self._schemas: dict[tuple[str, str], Schema] = {}

    def register(self, schema: Schema) -> None:
        key = self._key(schema.name, schema.version)
        if key in self._schemas:
            raise ValueError(f"schema already registered: {schema.name} v{schema.version}")
        self._validate_schema(schema)
        self._schemas[key] = schema

    def get(self, name: str, version: str) -> Schema | None:
        return self._schemas.get(self._key(name, version))

    def list_all(self) -> list[tuple[str, str]]:
        return sorted(self._schemas)

    @staticmethod
    def _key(name: str, version: str) -> tuple[str, str]:
        return (name.strip(), version.strip())

    @staticmethod
    def _validate_schema(schema: Schema) -> None:
        if not schema.name.strip():
            raise ValueError("schema name is required")
        if not schema.version.strip():
            raise ValueError("schema version is required")
        names: set[str] = set()
        for field in schema.fields:
            field_name = field.name.strip()
            if not field_name:
                raise ValueError("field name is required")
            if field_name in names:
                raise ValueError(f"duplicate field: {field_name}")
            if field.numeric_range is not None and field.numeric_range[0] > field.numeric_range[1]:
                raise ValueError(f"invalid numeric range for field: {field_name}")
            names.add(field_name)
