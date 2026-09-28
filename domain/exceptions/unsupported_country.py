class UnsupportedCountryError(Exception):
    def __init__(self, country_code: str, supported: list[str] | None = None):
        self.country_code = country_code
        self.supported = supported or []
        message = f"Unsupported country_code '{country_code}'"
        if self.supported:
            message += f". Supported countries: {', '.join(sorted(self.supported))}"
        super().__init__(message)
