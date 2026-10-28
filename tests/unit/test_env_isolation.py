import os

import pytest

from tests import conftest

CHANGED_KEY = "ENV_ISOLATION_PROBE_CHANGED"
DELETED_KEY = "ENV_ISOLATION_PROBE_DELETED"
ADDED_KEY = "ENV_ISOLATION_PROBE_ADDED"


def test_restore_fixture_undoes_environment_changes_made_by_a_test():
    """Drives the autouse conftest fixture by hand, so the result does not depend on test order or worker.

    A key the test added is removed; a changed or deleted key gets its snapshot value back.
    """
    os.environ[CHANGED_KEY] = "before"
    os.environ[DELETED_KEY] = "before"
    # pytest keeps the fixture's generator function on __wrapped__; calling it skips the pytest fixture machinery.
    restore = getattr(conftest.restore_environ_after_test, "__wrapped__")()
    next(restore)  # the fixture's setup: takes the snapshot, then yields
    try:
        os.environ[ADDED_KEY] = "1"
        os.environ[CHANGED_KEY] = "after"
        del os.environ[DELETED_KEY]

        with pytest.raises(StopIteration):  # the fixture's teardown: restores the snapshot
            next(restore)

        assert ADDED_KEY not in os.environ
        assert os.environ[CHANGED_KEY] == "before"
        assert os.environ[DELETED_KEY] == "before"
    finally:
        for key in (ADDED_KEY, CHANGED_KEY, DELETED_KEY):
            os.environ.pop(key, None)
