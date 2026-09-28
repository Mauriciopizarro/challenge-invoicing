class FlakyFault:
    # Passed as a provider's fault_injector: simulates "fails N times, then
    # recovers" without magic values baked into request payloads.
    def __init__(self, fail_times: int, exc_factory):
        self.remaining = fail_times
        self.exc_factory = exc_factory

    def __call__(self):
        if self.remaining > 0:
            self.remaining -= 1
            raise self.exc_factory()


class AlwaysFailFault:
    def __init__(self, exc_factory):
        self.exc_factory = exc_factory

    def __call__(self):
        raise self.exc_factory()
