"""Create the retail schema and import CSV exports into a target database."""

import argparse
import csv
import os
from pathlib import Path

from sqlalchemy import create_engine, text


DATA_DIRECTORY = Path(__file__).parent
SCHEMA_FILE = DATA_DIRECTORY / "schema.sql"
EXPORT_DIRECTORY = DATA_DIRECTORY / "exports"
TABLE_NAMES = ("customers", "products", "orders", "order_items")


def load_rows(csv_file: Path) -> list[dict[str, str | None]]:
    """Read a CSV file and convert empty fields to SQL NULL values."""

    with csv_file.open(newline="", encoding="utf-8") as file:
        return [
            {column: value if value != "" else None for column, value in row.items()}
            for row in csv.DictReader(file)
        ]


def create_schema(connection) -> None:
    """Execute the schema statements one at a time."""

    for statement in SCHEMA_FILE.read_text(encoding="utf-8").split(";"):
        if statement := statement.strip():
            connection.execute(text(statement))


def table_row_counts(connection, quote) -> dict[str, int]:
    """Return the current number of rows in each exported table."""

    return {
        table_name: connection.execute(
            text(f"SELECT COUNT(*) FROM {quote(table_name)}")
        ).scalar_one()
        for table_name in TABLE_NAMES
    }


def import_table(connection, table_name: str, csv_file: Path, quote) -> int:
    """Import one CSV file into its matching table."""

    rows = load_rows(csv_file)
    if not rows:
        return 0

    columns = tuple(rows[0])
    quoted_columns = ", ".join(quote(column) for column in columns)
    parameters = ", ".join(f":{column}" for column in columns)
    statement = text(f"INSERT INTO {quote(table_name)} ({quoted_columns}) VALUES ({parameters})")
    connection.execute(statement, rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the retail schema and import its CSV exports.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="target database URL; defaults to DATABASE_URL")
    args = parser.parse_args()

    if not args.database_url:
        parser.error("set DATABASE_URL or pass --database-url")

    engine = create_engine(args.database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            create_schema(connection)
            quote = engine.dialect.identifier_preparer.quote
            row_counts = table_row_counts(connection, quote)

            if all(row_counts.values()):
                print("Data already loaded; leaving without import.")
                return

            if any(row_counts.values()):
                formatted_counts = ", ".join(
                    f"{table_name}={count}" for table_name, count in row_counts.items()
                )
                raise RuntimeError(
                    "Database contains a partial import; refusing to add duplicate data "
                    f"({formatted_counts})."
                )

            for table_name in TABLE_NAMES:
                csv_file = EXPORT_DIRECTORY / f"{table_name}.csv"
                row_count = import_table(connection, table_name, csv_file, quote)
                print(f"Imported {row_count} rows into {table_name}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
