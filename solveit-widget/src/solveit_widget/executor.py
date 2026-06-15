from __future__ import annotations

import ast
import contextlib
import io
import traceback

from .models import CellOutput


class Executor:
    def __init__(self) -> None:
        self.ns: dict = {}

    def reset(self) -> None:
        self.ns = {}

    def run(self, source: str) -> CellOutput:
        out = CellOutput()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            out.error = traceback.format_exc()
            return out

        last_expr = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body.pop()  # tree is a fresh parse — pop() is safe

        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(tree, "<cell>", "exec"), self.ns)
                if last_expr is not None:
                    value = eval(
                        compile(ast.Expression(last_expr.value), "<cell>", "eval"),
                        self.ns,
                    )
                    if value is not None:
                        out.result_repr = repr(value)
                        html = getattr(value, "_repr_html_", None)
                        if callable(html):
                            try:
                                out.result_html = html()
                            except Exception:
                                out.result_html = None
        except Exception:
            out.error = traceback.format_exc()
        finally:
            out.stdout = stdout.getvalue()
            out.stderr = stderr.getvalue()
        return out
