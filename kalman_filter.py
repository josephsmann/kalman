import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import polars as pl
    import altair as alt

    return alt, mo, np, pl


@app.cell
def _(mo):
    mo.md(r"""
    # Kalman Filters: An Interactive Introduction

    A **Kalman filter** is a recursive algorithm that estimates the hidden state of a
    linear dynamical system from noisy measurements. At each step it fuses two pieces
    of information:

    1. A **prediction** from a physical model of how the state evolves.
    2. A **measurement** of (some function of) the state, corrupted by noise.

    The filter weighs these two by their respective uncertainties and produces an
    estimate that is *provably optimal* (minimum mean squared error) for linear
    Gaussian systems.

    ## The setup

    We model a hidden state $x_k \in \mathbb{R}^n$ evolving as

    $$x_k = F\,x_{k-1} + w_k, \qquad w_k \sim \mathcal{N}(0, Q)$$

    and a measurement $z_k \in \mathbb{R}^m$

    $$z_k = H\,x_k + v_k, \qquad v_k \sim \mathcal{N}(0, R).$$

    - $F$ — state-transition matrix (the dynamics)
    - $H$ — observation matrix (what we get to see)
    - $Q$ — process noise covariance (how much we trust the model)
    - $R$ — measurement noise covariance (how much we trust the sensor)
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## The two-step recursion

    Let $\hat{x}_{k|k-1}$ be the estimate before seeing measurement $k$, and
    $\hat{x}_{k|k}$ the estimate after. Same for the covariance $P$.

    **Predict** — push the previous estimate through the dynamics:

    $$\hat{x}_{k|k-1} = F\,\hat{x}_{k-1|k-1}$$
    $$P_{k|k-1} = F\,P_{k-1|k-1}\,F^\top + Q$$

    **Update** — correct the prediction with the new measurement:

    $$y_k = z_k - H\,\hat{x}_{k|k-1} \quad \text{(innovation)}$$
    $$S_k = H\,P_{k|k-1}\,H^\top + R \quad \text{(innovation covariance)}$$
    $$K_k = P_{k|k-1}\,H^\top\,S_k^{-1} \quad \text{(Kalman gain)}$$
    $$\hat{x}_{k|k} = \hat{x}_{k|k-1} + K_k\,y_k$$
    $$P_{k|k} = (I - K_k\,H)\,P_{k|k-1}$$

    The **Kalman gain** $K_k$ is the key. When the measurement is precise
    ($R$ small), $K_k \to H^{-1}$ and we trust the data. When the model is precise
    ($Q$ small, $P$ shrinks), $K_k \to 0$ and we trust the prediction.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## A worked example: tracking a 1D object with constant velocity
    """)
    return


@app.cell
def _(mo):
    model_choice = mo.ui.dropdown(
        options={
            "Constant velocity — state = [position, velocity], observe position": "cv",
            "Constant position (random walk) — state = [position, velocity], observe position": "cp",
            "Damped oscillator — state = [position, velocity], observe position": "osc",
            "Custom — edit F, H, x0 below": "custom",
        },
        value="Constant velocity — state = [position, velocity], observe position",
        label="Dynamics model",
    )
    F_widget = mo.ui.matrix(value=[[1.0, 1.0], [0.0, 1.0]], step=0.1, label="F")
    H_widget = mo.ui.matrix(value=[[1.0, 0.0]], step=0.1, label="H")
    x0_widget = mo.ui.matrix(value=[[0.0], [1.0]], step=0.5, label="x0")
    mo.vstack([
        model_choice,
        mo.md("**F — state transition** (used directly when model = Custom; presets override it):"),
        F_widget,
        mo.md("**H — observation matrix:**"),
        H_widget,
        mo.md("**x0 — initial true state:**"),
        x0_widget,
    ])
    return F_widget, H_widget, model_choice, x0_widget


@app.cell
def _(F_widget, H_widget, mo, model_choice, np, x0_widget):
    def _build_model():
        choice = model_choice.value
        if choice == "cv":
            F_ = np.array([[1.0, 1.0], [0.0, 1.0]])
            H_ = np.array([[1.0, 0.0]])
        elif choice == "cp":
            F_ = np.array([[1.0, 0.0], [0.0, 0.0]])
            H_ = np.array([[1.0, 0.0]])
        elif choice == "osc":
            omega, zeta, dt_ = 0.3, 0.05, 1.0
            F_ = np.array([
                [1.0, dt_],
                [-omega**2 * dt_, 1.0 - 2 * zeta * omega * dt_],
            ])
            H_ = np.array([[1.0, 0.0]])
        else:
            F_ = np.array(F_widget.value, dtype=float)
            H_ = np.array(H_widget.value, dtype=float)
        x0_ = np.array(x0_widget.value, dtype=float).flatten()
        return F_, H_, x0_

    F_model, H_model, x0_model = _build_model()

    def _fmt(M):
        M2 = np.atleast_2d(M)
        rows = [" & ".join(f"{v:.3g}" for v in row) for row in M2]
        return r"\begin{bmatrix}" + r" \\ ".join(rows) + r"\end{bmatrix}"

    mo.md(rf"""
    ### Current model

    $$x_k = F\,x_{{k-1}} + w_k, \qquad z_k = H\,x_k + v_k$$

    $$F = {_fmt(F_model)} \qquad H = {_fmt(H_model)} \qquad x_0 = {_fmt(x0_model.reshape(-1,1))}$$
    """)
    return F_model, H_model, x0_model


@app.cell
def _(mo):
    process_noise = mo.ui.slider(0.001, 1.0, value=0.05, step=0.001, label="Process noise Q (model uncertainty)")
    meas_noise = mo.ui.slider(0.1, 20.0, value=4.0, step=0.1, label="Measurement noise R (sensor noise)")
    n_steps = mo.ui.slider(20, 200, value=80, step=10, label="Number of time steps")
    seed = mo.ui.slider(0, 50, value=7, step=1, label="Random seed")
    mo.vstack([process_noise, meas_noise, n_steps, seed])
    return meas_noise, n_steps, process_noise, seed


@app.cell
def _(
    F_model,
    H_model,
    meas_noise,
    n_steps,
    np,
    process_noise,
    seed,
    x0_model,
):
    rng = np.random.default_rng(seed.value)

    F = F_model
    H = H_model
    dt = 1.0
    Q = process_noise.value * np.array([[dt**3 / 3, dt**2 / 2],
                                        [dt**2 / 2, dt]])
    R = np.array([[meas_noise.value]])

    N = n_steps.value
    true_states = np.zeros((N, 2))
    measurements = np.zeros(N)
    true_states[0] = x0_model
    for _k in range(1, N):
        _w = rng.multivariate_normal([0, 0], Q)
        true_states[_k] = F @ true_states[_k - 1] + _w
    for _k in range(N):
        measurements[_k] = (H @ true_states[_k])[0] + rng.normal(0, np.sqrt(R[0, 0]))

    x_est = np.zeros((N, 2))
    P_diag = np.zeros((N, 2))
    K_hist = np.zeros((N, 2))

    x = np.array([0.0, 0.0])
    P = np.eye(2) * 10.0
    I2 = np.eye(2)

    for _k in range(N):
        x = F @ x
        P = F @ P @ F.T + Q

        y = measurements[_k] - (H @ x)[0]
        S = H @ P @ H.T + R
        K = (P @ H.T) / S[0, 0]
        x = x + (K.flatten() * y)
        P = (I2 - K @ H) @ P

        x_est[_k] = x
        P_diag[_k] = np.diag(P)
        K_hist[_k] = K.flatten()
    return K_hist, N, P_diag, measurements, true_states, x_est


@app.cell
def _(N, P_diag, measurements, np, pl, true_states, x_est):
    t = np.arange(N)
    std_pos = np.sqrt(P_diag[:, 0])
    df = pl.DataFrame({
        "t": t,
        "true_position": true_states[:, 0],
        "true_velocity": true_states[:, 1],
        "measurement": measurements,
        "estimate": x_est[:, 0],
        "est_velocity": x_est[:, 1],
        "error": x_est[:, 0] - true_states[:, 0],
        "lower": x_est[:, 0] - 2 * std_pos,
        "upper": x_est[:, 0] + 2 * std_pos,
        "err_lower": -2 * std_pos,
        "err_upper":  2 * std_pos,
    })
    df
    return df, t


@app.cell
def _(alt, df):
    band = alt.Chart(df).mark_area(opacity=0.25, color="steelblue").encode(
        x=alt.X("t:Q", title="time step"),
        y=alt.Y("lower:Q", title="position"),
        y2="upper:Q",
    )
    truth = alt.Chart(df).mark_line(color="black", strokeWidth=2).encode(
        x="t:Q", y="true_position:Q",
        tooltip=["t", "true_position"],
    )
    meas = alt.Chart(df).mark_circle(color="firebrick", opacity=0.5, size=40).encode(
        x="t:Q", y="measurement:Q",
        tooltip=["t", "measurement"],
    )
    est = alt.Chart(df).mark_line(color="steelblue", strokeWidth=2).encode(
        x="t:Q", y="estimate:Q",
        tooltip=["t", "estimate"],
    )
    main_chart = (band + meas + truth + est).properties(
        width=700, height=300,
        title="Black = truth · Red = measurements · Blue = Kalman estimate (±2σ band — usually hidden behind the line at this scale)",
    )

    err_band = alt.Chart(df).mark_area(opacity=0.3, color="steelblue").encode(
        x=alt.X("t:Q", title="time step"),
        y=alt.Y("err_lower:Q", title="estimate − truth"),
        y2="err_upper:Q",
    )
    zero = alt.Chart(df).mark_rule(color="black", strokeDash=[4, 4]).encode(y=alt.datum(0))
    err_line = alt.Chart(df).mark_line(color="steelblue", strokeWidth=2).encode(
        x="t:Q", y="error:Q",
        tooltip=["t", "error"],
    )
    err_chart = (err_band + zero + err_line).properties(
        width=700, height=220,
        title="Estimation error with ±2σ band — the band should contain the error ~95% of the time",
    )

    alt.vconcat(main_chart, err_chart)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### What to look for

    - **Crank up R (sensor noise)** → the blue estimate becomes much smoother than the
      red dots. The filter learns to distrust the measurements and leans on its model.
    - **Crank up Q (process noise)** → the filter trusts the model less and tracks
      the measurements more closely (the blue line gets jumpier).
    - **The ±2σ band** is the filter's own report of its uncertainty. It shrinks fast
      at the start as information accumulates, then settles to a steady-state width.
    """)
    return


@app.cell
def _(K_hist, P_diag, alt, np, pl, t):
    gain_df = pl.DataFrame({
        "t": t,
        "K_position": K_hist[:, 0],
        "K_velocity": K_hist[:, 1],
        "sigma_pos": np.sqrt(P_diag[:, 0]),
        "sigma_vel": np.sqrt(P_diag[:, 1]),
    })

    gain_chart = alt.Chart(gain_df).transform_fold(
        ["K_position", "K_velocity"], as_=["component", "gain"]
    ).mark_line().encode(
        x=alt.X("t:Q", title="time step"),
        y=alt.Y("gain:Q", title="Kalman gain"),
        color=alt.Color("component:N", title=""),
        tooltip=["t:Q", "component:N", "gain:Q"],
    ).properties(width=700, height=200, title="Kalman gain converging to steady state")

    sigma_chart = alt.Chart(gain_df).transform_fold(
        ["sigma_pos", "sigma_vel"], as_=["component", "sigma"]
    ).mark_line().encode(
        x=alt.X("t:Q", title="time step"),
        y=alt.Y("sigma:Q", title="posterior std-dev"),
        color=alt.Color("component:N", title=""),
        tooltip=["t:Q", "component:N", "sigma:Q"],
    ).properties(width=700, height=200, title="Posterior uncertainty over time")

    alt.vconcat(gain_chart, sigma_chart)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Takeaways

    - A Kalman filter is just **Bayesian updating** for linear Gaussian systems —
      prior (prediction) + likelihood (measurement) = posterior (estimate).
    - The **Kalman gain** automatically balances model vs. measurement based on
      their relative uncertainties. You don't tune it; it falls out of the math.
    - The covariance $P$ evolves *independently of the measurements* — it depends
      only on $F$, $H$, $Q$, $R$. You can precompute the steady-state gain offline.
    - Extensions handle the cases this notebook didn't:
      **Extended KF** (linearize nonlinear $f, h$), **Unscented KF** (sigma points),
      **Particle filter** (drop the Gaussian assumption entirely).
    """)
    return


if __name__ == "__main__":
    app.run()
