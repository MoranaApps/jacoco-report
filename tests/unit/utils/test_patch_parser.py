import pytest

from jacoco_report.utils.patch_parser import changed_lines_from_patch


def test_additions_only_hunk_records_every_added_line():
    patch = "@@ -0,0 +1,2 @@\n+first\n+second"

    assert changed_lines_from_patch(patch) == frozenset({1, 2})


def test_modification_records_only_the_new_side_line():
    patch = "@@ -5,1 +5,1 @@\n-old text\n+new text"

    assert changed_lines_from_patch(patch) == frozenset({5})


def test_context_lines_advance_the_counter_without_being_recorded():
    patch = "@@ -1,3 +1,4 @@\n a\n+b\n c\n d"

    assert changed_lines_from_patch(patch) == frozenset({2})


def test_deletions_only_hunk_records_nothing():
    patch = "@@ -3,2 +2,0 @@\n-gone one\n-gone two"

    assert changed_lines_from_patch(patch) == frozenset()


def test_multiple_hunks_each_restart_the_counter_at_their_new_start():
    patch = "@@ -1,2 +1,2 @@\n-x\n+y\n z\n@@ -10,1 +11,2 @@\n w\n+n1\n+n2"

    assert changed_lines_from_patch(patch) == frozenset({1, 12, 13})


def test_no_newline_marker_after_removed_line_does_not_shift_numbers():
    patch = "@@ -1,1 +1,1 @@\n-a\n\\ No newline at end of file\n+b"

    assert changed_lines_from_patch(patch) == frozenset({1})


def test_no_newline_marker_after_added_line_does_not_shift_later_numbers():
    patch = "@@ -1,2 +1,4 @@\n-a\n+b\n+c\n\\ No newline at end of file\n d\n+e"

    assert changed_lines_from_patch(patch) == frozenset({1, 2, 4})


@pytest.mark.parametrize("separator", ["\x0b", "\x0c", "\x1c", "\x85", " ", " ", "\r"])
def test_line_break_characters_inside_a_line_do_not_split_it(separator):
    patch = f"@@ -0,0 +1,3 @@\n+a{separator}b\n+c\n+d"

    assert changed_lines_from_patch(patch) == frozenset({1, 2, 3})


def test_hunk_header_inside_an_added_line_is_not_taken_for_a_header():
    patch = "@@ -0,0 +1,3 @@\n+a @@ -1 +100 @@\n+b\n+c"

    assert changed_lines_from_patch(patch) == frozenset({1, 2, 3})


def test_crlf_line_endings_keep_the_numbers():
    patch = "@@ -0,0 +1,2 @@\r\n+a\r\n+b\r\n"

    assert changed_lines_from_patch(patch) == frozenset({1, 2})


def test_removed_line_starting_with_dashes_is_not_taken_for_a_file_header():
    patch = "@@ -1,2 +1,2 @@\n---dashes\n+++plus\n tail"

    assert changed_lines_from_patch(patch) == frozenset({1})


def test_lines_before_the_first_hunk_header_are_ignored():
    patch = "stray text\n@@ -1 +1 @@\n+x"

    assert changed_lines_from_patch(patch) == frozenset({1})


def test_empty_patch_records_nothing():
    assert changed_lines_from_patch("") == frozenset()
