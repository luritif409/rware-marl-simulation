from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .models import RobotState

STATUS_COLORS = {
    RobotState.IDLE.value: "#718096",
    RobotState.TO_SHELF.value: "#2A9D8F",
    RobotState.TO_GOAL.value: "#2563EB",
}
ANIMATION_SPEEDS = {"Lambat": 600, "Normal": 300, "Cepat": 120}


def aggregate_results(results) -> pd.DataFrame:
    rows = [result.to_summary() for result in results]
    raw = pd.DataFrame(rows)
    return (
        raw.groupby("Kebijakan", as_index=False)
        .agg(
            **{
                "Pesanan selesai": ("Pesanan selesai", "mean"),
                "Rata-rata waktu selesai": ("Rata-rata waktu selesai", "mean"),
                "Langkah terhambat": ("Langkah terhambat", "mean"),
                "Jarak tempuh": ("Jarak tempuh", "mean"),
                "Throughput": ("Throughput", "mean"),
            }
        )
        .round(3)
    )


def comparison_chart(summary: pd.DataFrame, metric: str):
    fig = px.bar(
        summary,
        x="Kebijakan",
        y=metric,
        color="Kebijakan",
        text_auto=".3s",
        color_discrete_map={
            "Baseline": "#4C78A8",
            "Kontribusi usulan": "#59A14F",
        },
    )
    fig.update_layout(showlegend=False, height=360, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def warehouse_figure(layout, frame: dict, title: str):
    fig = go.Figure()
    if layout.shelves:
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in layout.shelves],
                y=[p[1] for p in layout.shelves],
                mode="markers",
                name="Rak",
                marker=dict(symbol="square", size=28, color="#8D6E63"),
                hovertemplate="Rak (%{x}, %{y})<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[p[0] for p in layout.goals],
            y=[p[1] for p in layout.goals],
            mode="markers",
            name="Pengantaran",
            marker=dict(symbol="diamond", size=18, color="#F2C14E"),
        )
    )
    fig.add_trace(_robot_trace(frame))
    fig.add_trace(_cargo_trace(frame))
    fig.update_xaxes(range=[-0.5, layout.width - 0.5], dtick=1, showgrid=True)
    fig.update_yaxes(
        range=[layout.height - 0.5, -0.5], dtick=1, showgrid=True, scaleanchor="x", scaleratio=1
    )
    fig.update_layout(
        title=title,
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="#F8FAFC",
        legend=dict(orientation="h", y=1.05),
    )
    return fig


def _robot_trace(frame: dict) -> go.Scatter:
    robots = frame["robots"]
    return go.Scatter(
        x=[robot["x"] for robot in robots],
        y=[robot["y"] for robot in robots],
        mode="markers+text",
        name="Robot",
        text=[f"R{robot['robot_id']}" for robot in robots],
        textposition="middle center",
        textfont=dict(color="white", size=10),
        marker=dict(
            size=30,
            color=[STATUS_COLORS[robot["state"]] for robot in robots],
            line=dict(color="white", width=2),
        ),
        customdata=[[robot["state"], robot["order_id"]] for robot in robots],
        hovertemplate=(
            "%{text}<br>Status: %{customdata[0]}"
            "<br>Pesanan: %{customdata[1]}<extra></extra>"
        ),
    )


def _cargo_trace(frame: dict) -> go.Scatter:
    carrying = [
        robot for robot in frame["robots"]
        if robot["state"] == RobotState.TO_GOAL.value
    ]
    return go.Scatter(
        x=[robot["x"] + 0.28 for robot in carrying],
        y=[robot["y"] - 0.28 for robot in carrying],
        mode="markers",
        name="Barang dibawa",
        marker=dict(
            symbol="square",
            size=18,
            color="#E76F00",
            line=dict(color="#5C3500", width=2),
        ),
        customdata=[robot["order_id"] for robot in carrying],
        hovertemplate="Barang pesanan %{customdata}<extra></extra>",
    )


def sample_history(history: list[dict], max_frames: int = 300) -> tuple[list[dict], int]:
    """Kurangi frame tampilan dengan tetap mempertahankan awal dan akhir."""
    if not history:
        raise ValueError("Riwayat simulasi kosong.")
    if max_frames < 2:
        raise ValueError("Batas frame minimal 2.")
    stride = max(1, math.ceil((len(history) - 1) / (max_frames - 1)))
    frames = history[::stride]
    if frames[-1] is not history[-1]:
        frames.append(history[-1])
    return frames, stride


def warehouse_animation(
    layout, history: list[dict], policy: str, max_frames: int = 300
) -> tuple[go.Figure, int]:
    """Bangun satu Figure berisi seluruh frame untuk animasi di browser."""
    sampled, stride = sample_history(history, max_frames)

    def frame_title(frame: dict) -> str:
        return (
            f"{policy} — langkah {frame['step']} dari {history[-1]['step']}"
            f" · pesanan selesai {frame['completed']}"
        )

    fig = warehouse_figure(layout, sampled[0], frame_title(sampled[0]))
    fig.frames = [
        go.Frame(
            name=str(frame["step"]),
            data=[_robot_trace(frame), _cargo_trace(frame)],
            traces=[2, 3],
            layout=go.Layout(title_text=frame_title(frame)),
        )
        for frame in sampled
    ]

    def play_args(duration: int) -> list:
        return [
            None,
            {
                "frame": {"duration": duration, "redraw": True},
                "transition": {"duration": 0},
                "fromcurrent": True,
                "mode": "immediate",
            },
        ]

    fig.update_layout(
        margin=dict(l=20, r=20, t=70, b=150),
        height=650,
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                showactive=False,
                x=0,
                y=-0.12,
                buttons=[
                    dict(label="Play", method="animate", args=play_args(ANIMATION_SPEEDS["Normal"])),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "transition": {"duration": 0},
                                "mode": "immediate",
                            },
                        ],
                    ),
                ],
            ),
            dict(
                type="dropdown",
                x=0.39,
                y=-0.12,
                buttons=[
                    dict(label=label, method="animate", args=play_args(duration))
                    for label, duration in ANIMATION_SPEEDS.items()
                ],
            ),
        ],
        sliders=[
            dict(
                active=0,
                x=0,
                y=-0.24,
                len=1,
                currentvalue=dict(prefix="Langkah: "),
                steps=[
                    dict(
                        label=str(frame["step"]),
                        method="animate",
                        args=[
                            [str(frame["step"])],
                            {
                                "frame": {"duration": 0, "redraw": True},
                                "transition": {"duration": 0},
                                "mode": "immediate",
                            },
                        ],
                    )
                    for frame in sampled
                ],
            )
        ],
    )
    return fig, stride
