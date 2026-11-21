from __future__ import annotations

import random

from .config import SimulationConfig
from .models import Layout, Position


def _candidate_shelves(width: int, height: int) -> list[Position]:
    """Rak ditempatkan pada kolom berselang agar lorong tetap terhubung."""
    cells: list[Position] = []
    for x in range(2, width - 1, 3):
        for y in range(1, height - 3):
            cells.append((x, y))
    return cells


def _pickup_for(shelf: Position, width: int) -> Position:
    x, y = shelf
    if x + 1 < width:
        return (x + 1, y)
    return (x - 1, y)


def generate_layout(config: SimulationConfig, seed: int) -> Layout:
    config.validate()
    rng = random.Random(seed)
    candidates = _candidate_shelves(config.width, config.height)
    if config.n_shelves > len(candidates):
        raise ValueError(
            f"Jumlah rak terlalu besar. Maksimum {len(candidates)} untuk ukuran "
            f"{config.width} × {config.height}."
        )
    shelves = sorted(rng.sample(candidates, config.n_shelves))
    pickups = {shelf: _pickup_for(shelf, config.width) for shelf in shelves}

    # Zona bawah dipakai sebagai area awal robot dan titik pengantaran.
    goal_y = config.height - 1
    # Satu stasiun pengantaran per kolom memungkinkan eksperimen hingga
    # sejumlah robot yang sama dengan lebar gudang tanpa menumpuk di satu titik.
    goals = [(x, goal_y) for x in range(config.width)]
    start_y = config.height - 2
    start_candidates = [(x, start_y) for x in range(config.width)]
    if config.n_robots > len(start_candidates):
        raise ValueError(
            f"Jumlah robot terlalu besar. Maksimum {len(start_candidates)} untuk lebar gudang ini."
        )
    robot_starts = rng.sample(start_candidates, config.n_robots)
    return Layout(
        width=config.width,
        height=config.height,
        shelves=shelves,
        pickups=pickups,
        goals=goals,
        robot_starts=robot_starts,
    )
