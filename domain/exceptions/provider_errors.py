class ProviderError(Exception):
    pass


class ProviderTransientError(ProviderError):
    """Retryable failure: timeout or a 5xx-equivalent error from the external provider."""


class ProviderPermanentError(ProviderError):
    """Non-retryable failure: the provider rejected the request (bad payload/business rule)."""
