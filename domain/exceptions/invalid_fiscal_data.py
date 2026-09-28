class InvalidFiscalDataError(Exception):
    def __init__(self, country_code: str, reason: str):
        self.country_code = country_code
        self.reason = reason
        super().__init__(f"Invalid fiscal data for country_code '{country_code}': {reason}")
