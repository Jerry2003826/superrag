from __future__ import annotations


class MinioStore:
    """Placeholder for the Phase 1 storage interface.

    The local adapter is used by tests and development. The MinIO adapter keeps
    the object-store boundary explicit until service-backed tests are enabled.
    """

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
