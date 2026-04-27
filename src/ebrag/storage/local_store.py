from __future__ import annotations

from pathlib import Path


class LocalStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def _path_for(self, bucket: str, key: str) -> Path:
        safe_key = key.replace("\\", "/").lstrip("/")
        return self.root / bucket / safe_key

    def put_bytes(self, bucket: str, key: str, data: bytes) -> str:
        path = self._path_for(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        normalized_key = key.replace("\\", "/")
        return f"local://{bucket}/{normalized_key}"

    def put_file(self, bucket: str, key: str, path: Path) -> str:
        return self.put_bytes(bucket, key, path.read_bytes())

    def get_bytes(self, bucket: str, key: str) -> bytes:
        return self._path_for(bucket, key).read_bytes()

    def exists(self, bucket: str, key: str) -> bool:
        return self._path_for(bucket, key).exists()
