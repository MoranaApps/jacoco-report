"""
Static guard: every line the action prints goes through logging or the escaped workflow-command helpers,
so no other code writes to stdout or stderr directly.
"""

import ast
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# Both modules own the action's output channels: gh_action.py writes escaped workflow commands, and
# logging_config.py owns the log handler's stream.
EXEMPT_FILES = {"jacoco_report/utils/gh_action.py", "jacoco_report/utils/logging_config.py"}

STREAM_NAMES = {"stdout", "stderr", "__stdout__", "__stderr__"}
PPRINT_NAMES = {"print", "pprint"}
EXIT_NAMES = {"exit", "quit", "SystemExit"}


def _is_name(node: ast.AST, *names: str) -> bool:
    return isinstance(node, ast.Name) and node.id in names


def _is_attribute_of(node: ast.AST, owner: str, match: Callable[[str], bool]) -> bool:
    return isinstance(node, ast.Attribute) and _is_name(node.value, owner) and match(node.attr)


def _is_int_valued(node: ast.AST) -> bool:
    """True when the expression always evaluates to an int: int or bool literals, unary +/- on those, and an
    if-else whose both branches are int-valued. Anything else is unknown and not int-valued."""
    if isinstance(node, ast.Constant):
        return type(node.value) in (int, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _is_int_valued(node.operand)
    if isinstance(node, ast.IfExp):
        return _is_int_valued(node.body) and _is_int_valued(node.orelse)
    return False


def _stream_argument(call: ast.Call) -> ast.AST | None:
    """Return the stream argument of a StreamHandler call, or None when it is not given."""
    if call.args:
        return call.args[0]
    return next((keyword.value for keyword in call.keywords if keyword.arg == "stream"), None)


def _is_direct_output(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        func = node.func
        if _is_name(func, *PPRINT_NAMES):  # print(...) and pprint(...)
            return True
        if _is_attribute_of(func, "sys", lambda attr: attr == "exit") or _is_name(func, *EXIT_NAMES):
            # An exit argument that is not int-valued is printed to stderr: str, f-string, variable, None.
            return bool(node.args) and not _is_int_valued(node.args[0])
        if _is_name(func, "StreamHandler") or (isinstance(func, ast.Attribute) and func.attr == "StreamHandler"):
            stream = _stream_argument(node)
            return stream is None or (isinstance(stream, ast.Constant) and stream.value is None)
        return False
    if isinstance(node, ast.Attribute):
        return (
            _is_attribute_of(node, "sys", lambda attr: attr in STREAM_NAMES)
            or _is_attribute_of(node, "traceback", lambda attr: attr.startswith("print_"))
            or _is_attribute_of(node, "pprint", lambda attr: attr == "pprint")
            or _is_attribute_of(node, "os", lambda attr: attr == "write")
        )
    if isinstance(node, ast.ImportFrom):
        if node.module == "sys":
            return any(alias.name in STREAM_NAMES for alias in node.names)
        if node.module == "traceback":
            return any(alias.name.startswith("print_") for alias in node.names)
    return False


def _direct_output_lines(source: str) -> list[int]:
    """Return the line numbers, in order, that make a direct output call or reference."""
    tree = ast.parse(source)
    return sorted({node.lineno for node in ast.walk(tree) if _is_direct_output(node)})


def _find_direct_output(root: Path) -> list[str]:
    """Return `file:line: text` for every direct output call in main.py and jacoco_report/, minus the exempt files."""
    files = [root / "main.py", *(root / "jacoco_report").rglob("*.py")]
    hits = []
    for path in sorted(files):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in EXEMPT_FILES:
            continue
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for number in _direct_output_lines(source):
            hits.append(f"{relative}:{number}: {lines[number - 1].strip()}")
    return hits


def test_no_direct_output_outside_exempt_files():
    """No file other than the exempt ones writes to stdout or stderr directly."""
    assert _find_direct_output(REPO_ROOT) == []


DIRECT_OUTPUT_LINES = [
    "print('x')",
    "sys.stdout.write('x')",
    "sys.stderr.write('x')",
    "handler = logging.StreamHandler(sys.stderr)",
    "from sys import stdout",
    "from sys import stderr",
    "traceback.print_exc()",
    "traceback.print_stack()",
    "pprint.pprint({})",
    "pprint({})",
    "os.write(1, b'x')",
    "sys.exit('boom')",
    "sys.exit(f'boom {code}')",
    "sys.exit('a' + 'b')",
    'sys.exit(f"x")',
    'sys.exit("msg")',
    "sys.exit(-code)",
    "sys.exit(1 if fail else 'boom')",
    "sys.exit(1 if fail else code)",
    "sys.exit(1 if fail else 0.5)",
    "sys.exit(not code)",
    "sys.exit(code)",
    "sys.exit(None)",
    "exit('boom')",
    "exit(code)",
    "quit(code)",
    "quit('boom')",
    "SystemExit(code)",
    "raise SystemExit('boom')",
    "raise SystemExit(code)",
    "logging.StreamHandler()",
    "StreamHandler()",
]


@pytest.mark.parametrize("line", DIRECT_OUTPUT_LINES, ids=lambda line: line.replace(" ", ""))
def test_direct_output_in_another_file_is_reported(tmp_path, line):
    """The guard fails for each kind of direct output in a file that is not exempt."""
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    (tmp_path / "jacoco_report").mkdir()
    (tmp_path / "jacoco_report" / "other.py").write_text(line + "\n", encoding="utf-8")

    assert _find_direct_output(tmp_path) == [f"jacoco_report/other.py:1: {line}"]


@pytest.mark.parametrize(
    "line",
    [
        "sys.exit(1)",
        "sys.exit(0)",
        "sys.exit()",
        "sys.exit(-1)",
        "sys.exit(+1)",
        "sys.exit(True)",
        "sys.exit(False)",
        "sys.exit(1 if fail else 0)",
        "sys.exit(-1 if fail else 0)",
        "sys.exit(True if fail else -1)",
        "sys.exit(1 if a else (2 if b else 0))",
        "exit(0)",
        "quit(1)",
        "raise SystemExit(1)",
        "SystemExit()",
        "logging.StreamHandler(handler_stream)",
        "logging.info('ok')",
        "traceback.format_exc()",
        "print_summary()",
        "os.path.join('a', 'b')",
    ],
)
def test_ordinary_calls_are_not_reported(tmp_path, line):
    """Calls that do not write to a standard stream are not flagged."""
    (tmp_path / "main.py").write_text(line + "\n", encoding="utf-8")

    assert _find_direct_output(tmp_path) == []


def test_exempt_files_are_not_reported(tmp_path):
    """Direct output in the exempt files is allowed."""
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    (tmp_path / "jacoco_report" / "utils").mkdir(parents=True)
    for exempt in EXEMPT_FILES:
        (tmp_path / exempt).write_text("print('x')\nsys.stdout.flush()\n", encoding="utf-8")

    assert _find_direct_output(tmp_path) == []
