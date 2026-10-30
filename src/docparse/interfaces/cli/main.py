from __future__ import annotations

import typer

from .commands import chunks, parse, serve

app = typer.Typer(
    help="docparse: documents in, structured blocks with provenance out.", no_args_is_help=True
)
app.command()(parse.parse)
app.command()(chunks.chunks)
app.command()(serve.serve)

if __name__ == "__main__":
    app()
