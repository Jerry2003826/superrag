from __future__ import annotations

from typing import Annotated

from pydantic import Field

StableId = Annotated[str, Field(pattern=r"^[A-Z]{1,5}[0-9]{8}$")]
