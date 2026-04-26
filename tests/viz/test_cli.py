"""`zipmould viz serve` is registered as a Typer subcommand."""

from __future__ import annotations

from typer.testing import CliRunner

from zipmould.cli import app


def test_viz_serve_help_lists_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["viz", "serve", "--help"])
    assert result.exit_code == 0
    out = result.stdout
    assert "--host" in out
    assert "--port" in out
