import pytest
from pathlib import Path

def test_extract_txt(tmp_path):
    from backend.extractor import extract_text
    f = tmp_path / "test.txt"
    f.write_text("Hello clinical world.")
    result = extract_text(str(f))
    assert "Hello clinical world." in result

def test_extract_returns_string_for_unknown_type(tmp_path):
    from backend.extractor import extract_text
    f = tmp_path / "test.xyz"
    f.write_bytes(b"some binary data")
    result = extract_text(str(f))
    assert isinstance(result, str)  # never raises, always returns str

def test_extract_empty_returns_empty_string(tmp_path):
    from backend.extractor import extract_text
    f = tmp_path / "empty.txt"
    f.write_text("")
    result = extract_text(str(f))
    assert result == ""
