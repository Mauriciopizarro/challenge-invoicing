#!/bin/sh
exec rq worker invoices --url "$REDIS_URL" --worker-class rq.worker.SimpleWorker
