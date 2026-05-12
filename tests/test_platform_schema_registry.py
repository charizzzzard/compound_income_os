from __future__ import annotations

import unittest

from src.platform.schema_registry import FieldSpec, Schema, SchemaRegistry


class PlatformSchemaRegistryTests(unittest.TestCase):
    def test_register_and_get_schema(self) -> None:
        registry = SchemaRegistry()
        schema = Schema("positions", "1", (FieldSpec("ticker"), FieldSpec("weight", numeric_range=(0, 100)),))

        registry.register(schema)

        self.assertEqual(registry.get("positions", "1"), schema)

    def test_list_all_is_sorted_by_name_and_version(self) -> None:
        registry = SchemaRegistry()
        registry.register(Schema("scores", "2", (FieldSpec("ticker"),)))
        registry.register(Schema("positions", "1", (FieldSpec("ticker"),)))

        self.assertEqual(registry.list_all(), [("positions", "1"), ("scores", "2")])

    def test_duplicate_schema_registration_fails(self) -> None:
        registry = SchemaRegistry()
        schema = Schema("scores", "1", (FieldSpec("ticker"),))
        registry.register(schema)

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(schema)

    def test_invalid_field_contracts_fail_fast(self) -> None:
        registry = SchemaRegistry()

        with self.assertRaisesRegex(ValueError, "duplicate field"):
            registry.register(Schema("scores", "1", (FieldSpec("ticker"), FieldSpec("ticker"))))

        with self.assertRaisesRegex(ValueError, "invalid numeric range"):
            registry.register(Schema("scores", "2", (FieldSpec("score", numeric_range=(100, 0)),)))


if __name__ == "__main__":
    unittest.main()
