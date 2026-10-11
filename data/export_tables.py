"""Export the retail database tables to CSV files."""

import argparse
import csv
import os
from pathlib import Path

from sqlalchemy import create_engine, text


DEFAULT_ENV_FILE = Path(__file__).with_name(".env")
DEFAULT_OUTPUT_DIRECTORY = Path(__file__).with_name("exports")
TABLE_NAMES = ("customers", "orders", "products", "order_items")


def load_database_url(env_file: Path) -> str:
    """Read DATABASE_URL from the environment or a dotenv-style file."""

    if database_url := os.environ.get("DATABASE_URL"):
        return database_url

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1]

    raise RuntimeError(f"DATABASE_URL is not set in the environment or {env_file}.")


def export_tables(database_url: str, output_directory: Path) -> None:
    """Run SELECT * for each known table and write its rows to a CSV file."""

    output_directory.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        quote = engine.dialect.identifier_preparer.quote
        with engine.connect() as connection:
            for table_name in TABLE_NAMES:
                result = connection.execute(text(f"SELECT * FROM {quote(table_name)}"))
                output_file = output_directory / f"{table_name}.csv"

                with output_file.open("w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(result.keys())
                    writer.writerows(row for row in result)

                print(f"Exported {table_name} to {output_file}")
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export retail database tables to CSV files.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="dotenv file containing DATABASE_URL")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIRECTORY, help="directory for generated CSV files")
    args = parser.parse_args()

    export_tables(load_database_url(args.env_file), args.output_dir)


if __name__ == "__main__":
    main()
