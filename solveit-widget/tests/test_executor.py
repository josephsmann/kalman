from solveit_widget.executor import Executor


def test_captures_stdout():
    ex = Executor()
    out = ex.run("print('hello')")
    assert out.stdout.strip() == "hello"
    assert out.error is None


def test_last_expression_repr():
    ex = Executor()
    out = ex.run("1 + 2")
    assert out.result_repr == "3"


def test_no_result_for_statement():
    ex = Executor()
    out = ex.run("x = 5")
    assert out.result_repr == ""


def test_persistent_namespace():
    ex = Executor()
    ex.run("x = 41")
    out = ex.run("x + 1")
    assert out.result_repr == "42"


def test_error_is_captured_not_raised():
    ex = Executor()
    out = ex.run("1 / 0")
    assert out.error is not None
    assert "ZeroDivisionError" in out.error


def test_syntax_error_captured():
    ex = Executor()
    out = ex.run("def (")
    assert out.error is not None
    assert "SyntaxError" in out.error


def test_rich_html_repr():
    ex = Executor()
    src = (
        "class R:\n"
        "    def _repr_html_(self):\n"
        "        return '<b>hi</b>'\n"
        "R()"
    )
    out = ex.run(src)
    assert out.result_html == "<b>hi</b>"


def test_reset_clears_namespace():
    ex = Executor()
    ex.run("x = 1")
    ex.reset()
    out = ex.run("x")
    assert "NameError" in out.error


def test_stdout_captured_on_error():
    ex = Executor()
    out = ex.run("print('before')\n1/0")
    assert "before" in out.stdout
    assert "ZeroDivisionError" in out.error


def test_none_last_expression_no_repr():
    ex = Executor()
    out = ex.run("None")
    assert out.result_repr == ""
