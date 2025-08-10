import typer.testing
import enjam.main

runner = typer.testing.CliRunner()


def test_convert_all_mkv_vcodec_copy(tmp_path):
    """ Convert all mkv files in test directory. """
    result = runner.invoke(enjam.main.app, [
        "--pattern", "*.mkv",
        # "--no-write-log",
        # "--no-skip-errors"
        "--verbose",
        "--vcodec", 'copy',
        "--dst", str(tmp_path)  # write files to temporary dir
    ], catch_exceptions=False)
    print(result.stdout)
    assert result.exit_code == 0
    # 64pix.mkv should be processed successfully
    assert "Successfully processed 1 files" in result.stdout
    # Two empty files should report error
    assert "Failed to process 2 files" in result.stdout


def test_convert_all_mkv_vcodec_libx264(tmp_path):
    """ Convert all mkv files in test directory. """
    result = runner.invoke(enjam.main.app, [
        "--pattern", "*.mkv",
        # "--no-write-log",
        # "--no-skip-errors"
        "--verbose",
        "--vcodec", 'libx264',
        "--dst", str(tmp_path)  # write files to temporary dir
    ], catch_exceptions=False)
    print(result.stdout)
    assert result.exit_code == 0
    # 64pix.mkv should be processed successfully
    assert "Successfully processed 1 files" in result.stdout
    # Two empty files should report error
    assert "Failed to process 2 files" in result.stdout


def test_wrong_vbitrate_multiplier(tmp_path):
    """
    When incorrect vbitrate multiplier is given, file should not be processed.
    """
    result = runner.invoke(enjam.main.app, [
        "--pattern", "64pix.mkv",  # convert single file
        # "--no-write-log",
        "--no-skip-errors",
        "--vbitrate=x24g",  # NOTE: WRONG FORMAT
        "--verbose",
        "--vcodec", 'copy',
        "--dst", str(tmp_path)  # write files to temporary dir
    ], catch_exceptions=True)
    print(result.stdout)
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert 'Wrong vbitrate format "x24g"' in result.stdout


def test_correct_vbitrate_multiplier(tmp_path):
    """
    When correct vbitrate multiplier is given, file should be processed.
    """
    result = runner.invoke(enjam.main.app, [
        "--pattern", "64pix.mkv",  # convert single file
        # "--no-write-log",
        "--no-skip-errors",
        "--vbitrate=x24k",  # set output vbitrate to 64*64*24000
        "--verbose",
        "--vcodec", 'copy',
        "--dst", str(tmp_path)  # write files to temporary dir
    ], catch_exceptions=True)
    print(result.stdout)
    assert result.exit_code == 0
    assert "Successfully processed 1 files" in result.stdout
    assert "Failed to process " not in result.stdout

