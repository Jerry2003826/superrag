from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ebrag.db import models as _models
from ebrag.db.base import Base
from ebrag.db.session import get_engine
from ebrag.logging import configure_logging
from ebrag.settings import load_settings

_ = _models

app = typer.Typer(
    name="ebrag",
    help="Evidence-grounded biomedical systematic review RAG engine.",
    no_args_is_help=True,
)
console = Console()

ConfigOption = Annotated[
    Path | None,
    typer.Option("--config", "-c", help="Path to a YAML configuration file."),
]


@app.callback()
def main() -> None:
    configure_logging()


@app.command("init-db")
def init_db(config: ConfigOption = None) -> None:
    settings = load_settings(config)
    engine = get_engine(settings.database.url)
    Base.metadata.create_all(engine)
    console.print(f"Initialized database metadata for {settings.project.name}")


if __name__ == "__main__":
    app()
