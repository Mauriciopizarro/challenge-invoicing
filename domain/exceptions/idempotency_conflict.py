class IdempotencyConflict(Exception):
    def __init__(self, idempotency_key: str):
        self.idempotency_key = idempotency_key
        super().__init__(f"An invoice with Idempotency-Key '{idempotency_key}' already exists")
