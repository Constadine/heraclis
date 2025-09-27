"""
Tests to verify that the SQLAlchemy schema from models.py matches the actual database schema.
"""

from sqlalchemy import create_engine, inspect

from heraclis.models import Base


def test_schema() -> None:
    # Create an in-memory SQLite database and generate the schema from models
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    # Build expected schema from models metadata
    expected_schema = {}
    for table_name, table in Base.metadata.tables.items():
        expected_schema[table_name] = sorted([col.name for col in table.columns])

    # Build actual schema from the database
    actual_schema = {}
    for table in inspector.get_table_names():
        cols = [col["name"] for col in inspector.get_columns(table)]
        actual_schema[table] = sorted(cols)

    # Compare expected vs actual schemas
    for table, expected_columns in expected_schema.items():
        assert table in actual_schema, f"Table '{table}' not found in actual schema."
        assert expected_columns == actual_schema[table], (
            f"Mismatch in columns for table '{table}'. Expected {expected_columns}, got {actual_schema[table]}."
        )

    print("All schema tests passed!")


if __name__ == "__main__":
    test_schema()
