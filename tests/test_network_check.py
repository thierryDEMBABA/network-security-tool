import pytest
from network_check import is_valid_port, check_port
def test_valid_port():
    assert is_valid_port(443) is True
def test_invalid_port():
    assert is_valid_port(70000) is False
    assert is_valid_port(0) is False
def test_reject_invalid_port():
    with pytest.raises(ValueError):
        check_port("127.0.0.1", 70000)
