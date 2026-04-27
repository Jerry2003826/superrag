from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy import select

from ebrag.db import models
from ebrag.db import models as _models
from ebrag.db.base import Base
from ebrag.db.session import get_engine, session_scope
from ebrag.indexing.build_indexes import build_indexes
from ebrag.logging import configure_logging
from ebrag.providers import build_indexers
from ebrag.settings import load_settings

_ = _models

app = typer.Typer(
    name="ebrag",
    help="Evidence-grounded biomedical systematic review RAG engine.",
    no_args_is_help=True,
)
console = Console()
index_app = typer.Typer(help="Index maintenance commands.")
app.add_typer(index_app, name="index")

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


@index_app.command("rebuild")
def rebuild_indexes(
    paper_id: Annotated[
        str | None,
        typer.Option("--paper-id", help="Only rebuild indexes for one paper id."),
    ] = None,
    config: ConfigOption = None,
) -> None:
    settings = load_settings(config)
    with session_scope() as session:
        chunk_query = select(models.Chunk)
        span_query = select(models.EvidenceSpan)
        result_query = select(models.Result)
        if paper_id is not None:
            chunk_query = chunk_query.where(models.Chunk.paper_id == paper_id)
            span_query = span_query.where(models.EvidenceSpan.paper_id == paper_id)
            result_query = result_query.where(models.Result.paper_id == paper_id)
        opensearch_indexer, vector_indexer, graph_indexer = build_indexers(session, settings)
        result = build_indexes(
            chunks=list(session.scalars(chunk_query)),
            evidence_spans=list(session.scalars(span_query)),
            results=list(session.scalars(result_query)),
            opensearch_indexer=opensearch_indexer,
            vector_indexer=vector_indexer,
            graph_indexer=graph_indexer,
        )
    console.print(
        "Rebuilt indexes: "
        f"{result.lexical_documents} lexical documents, "
        f"{result.vector_points} vector points, "
        f"{result.graph_edges} graph edges"
    )


if __name__ == "__main__":
    app()
