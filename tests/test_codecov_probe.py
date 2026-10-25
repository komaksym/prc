from prc.codecov_probe import codecov_probe


def test_codecov_probe_returns_validated_marker() -> None:
    assert codecov_probe() == "codecov-verified"
