import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import polars as pl
    import altair as alt
    import plotly.graph_objects as go

    return alt, go, mo, np, pl


@app.cell
def _(mo):
    mo.md(r"""
    # Linear Dynamic Models

    A **linear dynamic model** describes how a system's *state* evolves over time
    according to linear rules. It's the engine underneath Kalman filters, control
    theory, and much of signals processing.

    We'll build intuition for the **discrete-time** form (a state that jumps each
    time step), since that's exactly what a Kalman filter assumes.

    ## State-space form

    The state $x_k \in \mathbb{R}^n$ is a vector that fully summarizes the system at
    step $k$. It evolves as

    $$x_{k+1} = A\,x_k + B\,u_k$$

    - $x_k$ — the **state** (e.g. position *and* velocity)
    - $A$ — the **state-transition matrix**: the dynamics
    - $u_k$ — an external **input / control** (optional)
    - $B$ — how the input enters the state

    With no input ($u_k = 0$) the system just iterates $x_{k+1} = A x_k$, so

    $$x_k = A^k\,x_0.$$

    Everything about the long-run behavior is hidden in the powers of $A$ — which
    is to say, in its **eigenvalues**.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Eigenvalues decide everything

    Write $A = V \Lambda V^{-1}$ (eigen-decomposition). Then
    $A^k = V \Lambda^k V^{-1}$, and since $\Lambda$ is diagonal, $A^k$ is governed by
    $\lambda_i^k$ for each eigenvalue $\lambda_i$. For discrete-time systems:

    | Eigenvalue magnitude | Behavior |
    |---|---|
    | $\lvert\lambda\rvert < 1$ | mode **decays** to zero — *stable* |
    | $\lvert\lambda\rvert = 1$ | mode **persists** — marginally stable |
    | $\lvert\lambda\rvert > 1$ | mode **grows** without bound — *unstable* |

    **Complex** eigenvalues come in conjugate pairs and produce **oscillation**: the
    angle $\arg(\lambda)$ sets the rotation per step, the magnitude $\lvert\lambda\rvert$
    sets the envelope (decaying, steady, or growing spiral).

    The unit circle in the complex plane is the dividing line between stable and
    unstable. Let's see it.
    """)
    return


@app.cell
def _(mo):
    system_choice = mo.ui.dropdown(
        options={
            "Stable spiral (decaying oscillation)": "spiral_stable",
            "Marginal oscillator (constant orbit)": "oscillator",
            "Unstable spiral (growing oscillation)": "spiral_unstable",
            "Stable node (pure decay, no oscillation)": "node",
            "Saddle (one stable, one unstable direction)": "saddle",
            "Custom — edit the A matrix below": "custom",
        },
        value="Stable spiral (decaying oscillation)",
        label="Example system",
    )
    A_widget = mo.ui.matrix(
        value=[[0.9, -0.3], [0.3, 0.9]], step=0.1, label="A — state transition"
    )
    x0_widget = mo.ui.matrix(
        value=[[3.0], [0.0]], step=0.5, label="x0 — initial state"
    )
    steps = mo.ui.slider(10, 120, value=60, step=5, label="Time steps")
    mo.vstack([
        system_choice,
        mo.md("**A matrix** (used directly when system = Custom; presets override it):"),
        A_widget,
        mo.md("**Initial state x0:**"),
        x0_widget,
        steps,
    ])
    return A_widget, steps, system_choice, x0_widget


@app.cell
def _(A_widget, np, system_choice, x0_widget):
    def _build():
        c = system_choice.value
        if c == "spiral_stable":
            A_ = np.array([[0.9, -0.3], [0.3, 0.9]])
        elif c == "oscillator":
            _th = 0.25
            A_ = np.array([[np.cos(_th), -np.sin(_th)],
                           [np.sin(_th), np.cos(_th)]])
        elif c == "spiral_unstable":
            A_ = np.array([[1.03, -0.3], [0.3, 1.03]])
        elif c == "node":
            A_ = np.array([[0.85, 0.0], [0.0, 0.6]])
        elif c == "saddle":
            A_ = np.array([[1.15, 0.0], [0.0, 0.8]])
        else:
            A_ = np.array(A_widget.value, dtype=float)
        return A_

    A = _build()
    x0 = np.array(x0_widget.value, dtype=float).flatten()
    eigvals, eigvecs = np.linalg.eig(A)
    return A, eigvals, x0


@app.cell
def _(A, eigvals, mo, np):
    def _fmt(M):
        M2 = np.atleast_2d(M)
        _rows = [" & ".join(f"{v:.3g}" for v in row) for row in M2]
        return r"\begin{bmatrix}" + r" \\ ".join(_rows) + r"\end{bmatrix}"

    _mags = np.abs(eigvals)
    if _mags.max() < 1 - 1e-9:
        _verdict = "**stable** — every mode decays to the origin"
    elif _mags.max() > 1 + 1e-9:
        _verdict = "**unstable** — at least one mode grows without bound"
    else:
        _verdict = "**marginally stable** — a mode neither grows nor decays"

    _eig_str = ",\\ ".join(
        f"{v.real:.3g}{'+' if v.imag >= 0 else '-'}{abs(v.imag):.3g}i" if abs(v.imag) > 1e-9
        else f"{v.real:.3g}"
        for v in eigvals
    )

    mo.md(rf"""
    ### This system

    $$A = {_fmt(A)} \qquad x_{{k+1}} = A\,x_k$$

    **Eigenvalues:** $\lambda = {_eig_str}$ &nbsp;→&nbsp; magnitudes
    $\lvert\lambda\rvert = {', '.join(f'{m:.3g}' for m in _mags)}$.

    Verdict: {_verdict}.
    """)
    return


@app.cell
def _(A, np, steps, x0):
    _N = steps.value
    traj = np.zeros((_N, 2))
    traj[0] = x0
    for _k in range(1, _N):
        traj[_k] = A @ traj[_k - 1]
    return (traj,)


@app.cell
def _(alt, mo, np, pl, traj):
    _N = traj.shape[0]
    _ts_df = pl.DataFrame({
        "k": np.arange(_N),
        "x0": traj[:, 0],
        "x1": traj[:, 1],
    })

    _ts = alt.Chart(_ts_df).transform_fold(
        ["x0", "x1"], as_=["component", "value"]
    ).mark_line(point=True).encode(
        x=alt.X("k:Q", title="time step k"),
        y=alt.Y("value:Q", title="state component"),
        color=alt.Color("component:N", title=""),
        tooltip=["k:Q", "component:N", "value:Q"],
    ).properties(width=380, height=320, title="State over time")

    _phase_df = pl.DataFrame({
        "x0": traj[:, 0],
        "x1": traj[:, 1],
        "k": np.arange(_N),
    })
    _path = alt.Chart(_phase_df).mark_line(opacity=0.5, color="gray").encode(
        x=alt.X("x0:Q", title="x[0]"),
        y=alt.Y("x1:Q", title="x[1]"),
        order="k:Q",
    )
    _pts = alt.Chart(_phase_df).mark_circle(size=45).encode(
        x="x0:Q", y="x1:Q",
        color=alt.Color("k:Q", scale=alt.Scale(scheme="viridis"), title="step k"),
        tooltip=["k:Q", "x0:Q", "x1:Q"],
    )
    _phase = (_path + _pts).properties(
        width=380, height=320, title="Phase portrait (x[1] vs x[0])"
    )

    mo.hstack([_ts, _phase])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### What to watch

    - **Stable spiral** → the phase portrait spirals *inward* to the origin; the time
      series is a decaying sine wave. Eigenvalues are complex with $|\lambda| < 1$.
    - **Marginal oscillator** → a closed loop (an *orbit*); the time series is a clean
      sustained sinusoid. $|\lambda| = 1$ exactly — a pure rotation matrix.
    - **Unstable spiral** → spirals *outward*; oscillations grow. $|\lambda| > 1$.
    - **Node** → no rotation, just straight decay toward the origin along the
      eigenvector axes. Real eigenvalues, both $< 1$.
    - **Saddle** → grows along one eigenvector, shrinks along the other.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## The complex plane: where the eigenvalues live

    Stability is a geometry question: are the eigenvalues **inside the unit circle**?
    The plot below shows the unit circle and this system's eigenvalues. Drag the
    sliders to move a conjugate pair around and watch the resulting trajectory change
    character — magnitude controls growth/decay, angle controls oscillation speed.
    """)
    return


@app.cell
def _(mo):
    eig_mag = mo.ui.slider(0.5, 1.3, value=0.95, step=0.01, label="Eigenvalue magnitude |λ|")
    eig_angle = mo.ui.slider(0.0, 3.14, value=0.4, step=0.01, label="Eigenvalue angle arg(λ) [rad]")
    mo.vstack([eig_mag, eig_angle])
    return eig_angle, eig_mag


@app.cell
def _(eig_angle, eig_mag, np):
    _r = eig_mag.value
    _th = eig_angle.value
    # 2x2 real matrix with eigenvalues r*e^{±iθ}: a rotation-scaling block
    A_demo = _r * np.array([[np.cos(_th), -np.sin(_th)],
                            [np.sin(_th),  np.cos(_th)]])
    demo_traj = np.zeros((80, 2))
    demo_traj[0] = [3.0, 0.0]
    for _k in range(1, 80):
        demo_traj[_k] = A_demo @ demo_traj[_k - 1]
    return (demo_traj,)


@app.cell
def _(alt, demo_traj, eig_angle, eig_mag, mo, np, pl):
    _r = eig_mag.value
    _th = eig_angle.value

    _circle_pts = np.linspace(0, 2 * np.pi, 200)
    _circle_df = pl.DataFrame({
        "cx": np.cos(_circle_pts),
        "cy": np.sin(_circle_pts),
    })
    _eig_df = pl.DataFrame({
        "ex": [_r * np.cos(_th), _r * np.cos(-_th)],
        "ey": [_r * np.sin(_th), _r * np.sin(-_th)],
    })

    _unit = alt.Chart(_circle_df).mark_line(color="black", strokeDash=[4, 4]).encode(
        x=alt.X("cx:Q", title="Re(λ)", scale=alt.Scale(domain=[-1.4, 1.4])),
        y=alt.Y("cy:Q", title="Im(λ)", scale=alt.Scale(domain=[-1.4, 1.4])),
    )
    _eig_pts = alt.Chart(_eig_df).mark_circle(size=160, color="firebrick").encode(
        x="ex:Q", y="ey:Q", tooltip=["ex:Q", "ey:Q"],
    )
    _complex_plane = (_unit + _eig_pts).properties(
        width=360, height=360,
        title=f"Eigenvalues on the complex plane (|λ|={_r:.2f})",
    )

    _N = demo_traj.shape[0]
    _td = pl.DataFrame({"k": np.arange(_N), "x0": demo_traj[:, 0]})
    _resp = alt.Chart(_td).mark_line(point=True, color="steelblue").encode(
        x=alt.X("k:Q", title="time step k"),
        y=alt.Y("x0:Q", title="x[0]"),
        tooltip=["k:Q", "x0:Q"],
    ).properties(width=400, height=360, title="Resulting trajectory of x[0]")

    mo.hstack([_complex_plane, _resp])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Adding an input: forced response

    Real systems are driven. With a control input the recursion is
    $x_{k+1} = A x_k + B u_k$. The total response splits into:

    - the **free response** $A^k x_0$ (what the initial condition does on its own), plus
    - the **forced response** (the accumulated effect of all inputs).

    Below, a stable 1D system $x_{k+1} = a\,x_k + b\,u_k$ is driven by a step input.
    A stable system settles to a **steady state** $x_\infty = \dfrac{b\,u}{1-a}$.
    """)
    return


@app.cell
def _(mo):
    a_param = mo.ui.slider(0.0, 0.98, value=0.8, step=0.02, label="a (decay rate, |a|<1 for stability)")
    b_param = mo.ui.slider(0.1, 2.0, value=1.0, step=0.1, label="b (input gain)")
    u_param = mo.ui.slider(0.0, 5.0, value=2.0, step=0.5, label="u (constant step input)")
    mo.vstack([a_param, b_param, u_param])
    return a_param, b_param, u_param


@app.cell
def _(a_param, alt, b_param, mo, np, pl, u_param):
    _a, _b, _u = a_param.value, b_param.value, u_param.value
    _N = 50
    _x = np.zeros(_N)
    for _k in range(1, _N):
        _x[_k] = _a * _x[_k - 1] + _b * _u
    _x_inf = _b * _u / (1 - _a) if abs(_a) < 1 else float("nan")

    _df = pl.DataFrame({"k": np.arange(_N), "x": _x})
    _line = alt.Chart(_df).mark_line(point=True, color="steelblue").encode(
        x=alt.X("k:Q", title="time step k"),
        y=alt.Y("x:Q", title="state x"),
        tooltip=["k:Q", "x:Q"],
    )
    _ss = alt.Chart(pl.DataFrame({"y": [_x_inf]})).mark_rule(
        color="firebrick", strokeDash=[5, 5]
    ).encode(y="y:Q")
    _chart = (_line + _ss).properties(
        width=700, height=300,
        title=f"Step response — settles to x∞ = b·u/(1−a) = {_x_inf:.2f} (red dashed line)",
    )
    mo.output.replace(_chart)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Oscillating mode + decaying mode (needs 3 dimensions)

    In 2-D you can't have one mode *oscillate* while another *separately decays* — an
    oscillation eats a whole complex-conjugate **pair** of eigenvalues, leaving none for an
    independent decaying mode. You need **three** state dimensions:

    $$A = \begin{bmatrix} r\cos\theta & -r\sin\theta & 0 \\ r\sin\theta & r\cos\theta & 0 \\ 0 & 0 & d \end{bmatrix}$$

    - The top-left **2x2 block** is a rotation by $\theta$ scaled by $r$ → eigenvalues
      $r\,e^{\pm i\theta}$. Set $r=1$ for a sustained orbit, $r<1$ for a decaying spiral.
    - The bottom-right **$d$** is the third (real) eigenvalue. With $0<d<1$ the $x_2$ mode
      dies out on its own.

    Watch the 3-D trajectory **collapse onto the oscillation plane** as the $x_2$ component
    decays to zero, leaving a pure orbit (or inward spiral if $r<1$).
    """)
    return


@app.cell
def _(mo):
    osc_r = mo.ui.slider(0.7, 1.05, value=1.0, step=0.01, label="r — oscillation magnitude (1 = sustained, <1 = decaying spiral)")
    osc_theta = mo.ui.slider(0.05, 1.2, value=0.4, step=0.01, label="θ — rotation per step [rad]")
    decay_d = mo.ui.slider(0.1, 0.95, value=0.7, step=0.01, label="d — decay rate of the third mode (0<d<1)")
    osc_steps = mo.ui.slider(20, 150, value=80, step=5, label="Time steps")
    mo.vstack([osc_r, osc_theta, decay_d, osc_steps])
    return decay_d, osc_r, osc_steps, osc_theta


@app.cell
def _(decay_d, np, osc_r, osc_steps, osc_theta):
    A3 = np.array([
        [osc_r.value * np.cos(osc_theta.value), -osc_r.value * np.sin(osc_theta.value), 0.0],
        [osc_r.value * np.sin(osc_theta.value),  osc_r.value * np.cos(osc_theta.value), 0.0],
        [0.0, 0.0, decay_d.value],
    ])
    eig3 = np.linalg.eigvals(A3)

    _N3 = osc_steps.value
    traj3 = np.zeros((_N3, 3))
    traj3[0] = [2.0, 0.0, 2.5]
    for _k in range(1, _N3):
        traj3[_k] = A3 @ traj3[_k - 1]
    return (traj3,)


@app.cell
def _(alt, go, mo, np, pl, traj3):
    _N3 = traj3.shape[0]

    _ts_df = pl.DataFrame({
        "k": np.arange(_N3),
        "x0 (oscillating)": traj3[:, 0],
        "x1 (oscillating)": traj3[:, 1],
        "x2 (decaying)": traj3[:, 2],
    })
    _ts = alt.Chart(_ts_df).transform_fold(
        ["x0 (oscillating)", "x1 (oscillating)", "x2 (decaying)"],
        as_=["component", "value"],
    ).mark_line().encode(
        x=alt.X("k:Q", title="time step k"),
        y=alt.Y("value:Q", title="state value"),
        color=alt.Color("component:N", title=""),
        tooltip=["k:Q", "component:N", "value:Q"],
    ).properties(width=720, height=260, title="All three components over time — x2 decays while x0,x1 oscillate")

    _fig = go.Figure()
    _fig.add_trace(go.Scatter3d(
        x=traj3[:, 0], y=traj3[:, 1], z=traj3[:, 2],
        mode="lines+markers",
        line=dict(color="royalblue", width=4),
        marker=dict(size=3, color=np.arange(_N3), colorscale="Viridis", showscale=True,
                    colorbar=dict(title="step k")),
        name="trajectory",
    ))
    _fig.add_trace(go.Scatter3d(
        x=[traj3[0, 0]], y=[traj3[0, 1]], z=[traj3[0, 2]],
        mode="markers", marker=dict(size=7, color="firebrick"), name="start",
    ))
    _fig.update_layout(
        height=460, margin=dict(l=0, r=0, t=30, b=0),
        title="3-D phase portrait — spiral collapses onto the x0–x1 oscillation plane (z→0)",
        scene=dict(xaxis_title="x0", yaxis_title="x1", zaxis_title="x2 (decaying)"),
    )

    mo.vstack([_ts, mo.as_html(_fig)])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## How this connects to Kalman filtering

    A Kalman filter assumes *exactly* this kind of linear dynamic model — the
    $F$ matrix in the Kalman notebook is the $A$ here:

    $$\underbrace{x_k = F\,x_{k-1} + w_k}_{\text{linear dynamics + process noise}}
    \qquad
    \underbrace{z_k = H\,x_k + v_k}_{\text{linear measurement + noise}}$$

    Everything you just explored carries over:

    - The **eigenvalues of $F$** govern whether the filter's *prediction* step grows,
      decays, or oscillates between measurements.
    - The **phase portrait** is the trajectory the filter is trying to track through
      the fog of measurement noise.
    - A stable $F$ means prediction errors shrink on their own; an unstable $F$ means
      the filter leans much harder on incoming measurements to stay locked on.

    A linear dynamic model is the "physics"; the Kalman filter is the optimal way to
    *estimate its state* when you can only see noisy pieces of it.
    """)
    return


if __name__ == "__main__":
    app.run()
