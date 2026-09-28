class InvoiceNotFoundError(Exception):
    def __init__(self, invoice_id):
        self.invoice_id = invoice_id
        super().__init__(f"Invoice '{invoice_id}' not found")
