from __future__ import annotations

import hashlib
from pathlib import Path

from ebrag.db import models
from ebrag.db.repositories import BaseRepository
from ebrag.storage.object_store import ObjectStore


def source_key_for(paper_id: str, source_path: Path) -> str:
    suffix = source_path.suffix.lower() or ".bin"
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()[:16]
    return f"{paper_id}/{digest}{suffix}"


class SourceAcquisition:
    def __init__(self, store: ObjectStore, bucket: str) -> None:
        self.store = store
        self.bucket = bucket

    def upload_source(
        self,
        *,
        repository: BaseRepository,
        paper: models.Paper,
        source_path: Path,
    ) -> str:
        key = source_key_for(paper.paper_id, source_path)
        uri = self.store.put_file(self.bucket, key, source_path)
        paper.full_text_available = True
        repository.create_audit_log(
            action="source.upload",
            target_type="paper",
            target_id=paper.paper_id,
            after={"object_uri": uri, "source_path": str(source_path)},
        )
        return uri
