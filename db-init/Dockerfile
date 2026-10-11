FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.sql import_tables.py ./
COPY exports ./exports

CMD ["python", "import_tables.py"]
