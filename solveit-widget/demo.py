import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from solveit_widget import SolveItWidget, ClaudeClient

    return ClaudeClient, SolveItWidget, mo


@app.cell
def _(mo):
    model_selector = mo.ui.dropdown(
        options={
            "Opus 4.8": "claude-opus-4-8",
            "Sonnet 4.6": "claude-sonnet-4-6",
            "Haiku 4.5": "claude-haiku-4-5",
        },
        value="Sonnet 4.6",
        label="Model",
    )
    model_selector
    return (model_selector,)


@app.cell
def _(ClaudeClient, SolveItWidget, mo, model_selector):
    widget = mo.ui.anywidget(
        SolveItWidget(
            path="my_session.solveit.json",
            llm=ClaudeClient(model=model_selector.value),
        )
    )
    widget
    return


if __name__ == "__main__":
    app.run()
