# Database initializer

This one-shot service prepares the MySQL database used by the Retail Support Assistant.

## What it does

- Creates the `retail_db` schema and its `customers`, `products`, `orders`, and `order_items` tables.
- Imports the matching CSV exports when every table is empty.
- Exits successfully without importing when every table already contains data.
- Fails when only some tables contain data, preventing a partial import from creating duplicates.

## How it works

Docker Compose waits for MySQL to pass its TCP health check, then starts this container. The container runs `import_tables.py` and exits when initialization is complete. Its data persists in the `mysql_data` Docker volume.

## Configuration

`db-init/.env.example` documents the service environment contract. Docker Compose injects `DATABASE_URL` using the MySQL settings in the root `.env` file.

For direct use, provide `DATABASE_URL` in the environment or pass it to `import_tables.py` with `--database-url`.
