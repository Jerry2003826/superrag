from __future__ import annotations

from typer.testing import CliRunner

from ebrag.cli import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "init-db" in result.output
    assert "index" in result.output


def test_cli_index_rebuild_help() -> None:
    result = CliRunner().invoke(app, ["index", "rebuild", "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
