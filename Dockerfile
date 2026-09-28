FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client curl gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/entrypoint.sh /app/worker_entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
