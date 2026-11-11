class PayBridgeError(Exception):
    """Unified error raised for gateway, validation, and webhook failures."""

    def __init__(self, message: str, *, code: str = "paybridge_error", gateway: str | None = None):
        super().__init__(message)
        self.code = code
        self.gateway = gateway
