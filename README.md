# Kalman Filters & Linear Dynamic Models

Interactive [marimo](https://marimo.io) notebooks for building intuition about state
estimation and the linear systems underneath it.

## Notebooks

- **`linear_dynamic_models.py`** — the foundation. State-space form
  `x_{k+1} = A x_k + B u_k`, how eigenvalues of `A` decide stability/oscillation,
  interactive phase portraits, a complex-plane eigenvalue playground, forced (step)
  response, and a 3-D example with one oscillating mode and one decaying mode.

- **`kalman_filter.py`** — the Kalman filter built on top of that model. The
  predict/update recursion, the Kalman gain, a live 1-D tracking demo with sliders for
  process and measurement noise, a selectable/custom dynamics model, and plots of the
  estimate, its ±2σ uncertainty band, the estimation error, and gain/covariance
  convergence.

## Running

These notebooks use [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv run marimo edit linear_dynamic_models.py
uv run marimo edit kalman_filter.py
```

Dependencies: `marimo`, `numpy`, `polars`, `altair`, `plotly`.
