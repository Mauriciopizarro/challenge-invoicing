class RecipientNotFoundError(Exception):
    def __init__(self, recipient_id):
        self.recipient_id = recipient_id
        super().__init__(f"Recipient '{recipient_id}' not found")
