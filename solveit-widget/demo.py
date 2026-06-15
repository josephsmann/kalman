import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from solveit_widget import SolveItWidget

    return SolveItWidget, mo


@app.cell
def _(SolveItWidget, mo):
    widget = mo.ui.anywidget(SolveItWidget(path="my_session.solveit.json"))
    widget
    return


if __name__ == "__main__":
    app.run()
