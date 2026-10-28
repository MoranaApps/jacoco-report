import os

from tests import conftest

CHANGED_KEY = "ENV_ISOLATION_PROBE_CHANGED"
DELETED_KEY = "ENV_ISOLATION_PROBE_DELETED"
ADDED_KEY = "ENV_ISOLATION_PROBE_ADDED"


def test_restore_environ_undoes_environment_changes_made_by_a_test():
    """A key the test added is removed; a changed or deleted key gets its snapshot value back."""
    os.environ[CHANGED_KEY] = "before"
    os.environ[DELETED_KEY] = "before"
    try:
        snapshot = conftest.snapshot_environ()
        os.environ[ADDED_KEY] = "1"
        os.environ[CHANGED_KEY] = "after"
        del os.environ[DELETED_KEY]

        conftest.restore_environ(snapshot)

        assert ADDED_KEY not in os.environ
        assert os.environ[CHANGED_KEY] == "before"
        assert os.environ[DELETED_KEY] == "before"
    finally:
        for key in (ADDED_KEY, CHANGED_KEY, DELETED_KEY):
            os.environ.pop(key, None)
