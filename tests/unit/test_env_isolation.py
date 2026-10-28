import os

# Captured at import, before any test runs; the probe tests below must not change these keys for the next test.
_ORIGINAL_LANG = os.environ.get("LANG")
_ORIGINAL_PATH = os.environ["PATH"]


def test_a_writes_and_deletes_environment_variables():
    """Leaks env changes on purpose: the autouse conftest fixture must undo them before the next test."""
    os.environ["ENV_ISOLATION_PROBE_ADDED"] = "1"
    os.environ["LANG"] = "probe"
    os.environ.pop("PATH")


def test_b_sees_environment_restored_by_previous_test():
    """Runs right after test_a: the added key is gone, and the changed and deleted keys are back as they were."""
    assert "ENV_ISOLATION_PROBE_ADDED" not in os.environ
    assert os.environ.get("LANG") == _ORIGINAL_LANG
    assert os.environ.get("PATH") == _ORIGINAL_PATH
