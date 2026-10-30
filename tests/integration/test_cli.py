import pytest
from typer.testing import CliRunner

from docparse.interfaces.cli.main import app

pytestmark = pytest.mark.integration


def test_cli_parse_writes_outputs(text_pdf, tmp_path):
    r = CliRunner().invoke(app, ["parse", str(text_pdf), "--out", str(tmp_path / "o")])
    assert r.exit_code == 0, r.output
    assert "gate=ok" in r.output
    assert (tmp_path / "o" / "report.md").exists() and (
        tmp_path / "o" / "report.chunks.jsonl"
    ).exists()
