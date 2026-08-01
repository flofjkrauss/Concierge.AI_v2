"""Tests for the application startup."""
from run import main

def test_main_prints_startup_message(capsys) -> None:
    main()

    captured = capsys.readouterr()

    assert captured.out == "Application started.\n"
    assert captured.err == ""
