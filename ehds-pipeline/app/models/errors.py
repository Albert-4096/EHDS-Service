class CoreSetError(Exception):
    """Raised when mandatory Core Set fields are missing; blocks pipeline execution."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
