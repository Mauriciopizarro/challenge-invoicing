class MerchantNotFoundError(Exception):
    def __init__(self, merchant_id):
        self.merchant_id = merchant_id
        super().__init__(f"Merchant '{merchant_id}' not found")
