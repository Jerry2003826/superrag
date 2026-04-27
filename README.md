# Evidence Bio RAG

Evidence-grounded biomedical systematic review RAG engine.

This repository is currently at Phase 0: runnable project skeleton, local
infrastructure, configuration, database session wiring, CLI entry point, and
quality gates.

## Quick Start

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
docker compose up -d
pytest
ruff check .
mypy
```

## CLI

```bash
ebrag --help
ebrag init-db
```

## Design Boundary

The final synthesis layer must only emit claims that can be traced to evidence
objects. Unsupported claims, uncited numeric claims, and wrong-scope claims are
blocked before release.
