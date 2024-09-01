from typer.testing import CliRunner

from enjam.main import app

runner = CliRunner()


def test_app(tmp_path):
    result = runner.invoke(app, [
        # "--pattern", "empty.mkv",
        # "--no-write-log",
        # "--no-skip-errors"
        "--verbose",
        "--dst", str(tmp_path)
    ], catch_exceptions=False)
    print(result.stdout)
    assert result.exit_code == 0
    assert "Successfully processed 1 files" in result.stdout
    assert "Failed to process 3 files" in result.stdout
    # assert "Hello Camila" in result.stdout


def test_wrong_vbitrate_multiplier(tmp_path):
    result = runner.invoke(app, [
        "--pattern", "64pix.gif",
        # "--no-write-log",
        "--no-skip-errors",
        "--vbitrate=x24g",  # NOTE: WRONG FORMAT
        "--verbose",
        "--dst", str(tmp_path)
    ], catch_exceptions=True)
    print(result.stdout)
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert 'Wrong vbitrate format "x24g"' in result.stdout


def test_correct_vbitrate_multiplier(tmp_path):
    result = runner.invoke(app, [
        "--pattern", "64pix.gif",
        # "--no-write-log",
        "--no-skip-errors",
        "--vbitrate=x24k",
        "--verbose",
        "--dst", str(tmp_path)
    ], catch_exceptions=True)
    print(result.stdout)
    assert result.exit_code == 0
    assert "Successfully processed 1 files" in result.stdout
    assert "Failed to process " not in result.stdout

