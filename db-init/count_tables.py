"""Print the row count for every table in the configured database."""

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine, text


DEFAULT_ENV_FILE = Path(__file__).with_name(".env")
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


def count_tables(database_url: str) -> list[tuple[str, int]]:
    """Return every table name and its row count."""

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        quote = engine.dialect.identifier_preparer.quote

        with engine.connect() as connection:
            return [
                (table_name, connection.execute(text(f"SELECT COUNT(*) FROM {quote(table_name)}")).scalar_one())
                for table_name in TABLE_NAMES
            ]
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Print row counts for every database table.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="dotenv file containing DATABASE_URL")
    args = parser.parse_args()

    print("TABLE\tROWS")
    for table_name, row_count in count_tables(load_database_url(args.env_file)):
        print(f"{table_name}\t{row_count}")


if __name__ == "__main__":
    main()
