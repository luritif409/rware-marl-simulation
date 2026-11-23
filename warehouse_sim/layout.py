from __future__ import annotations

import random

from .config import SimulationConfig
from .models import Layout, Position


def _candidate_shelves(width: int, height: int) -> list[Position]:
    """Dua kolom rak per blok, dipisahkan lorong seperti layout RWARE."""
    cells: list[Position] = []
    for x in range(1, width - 1):
        if x % 3 == 0:
            continue
        for y in range(1, height - 3):
            cells.append((x, y))
    return cells


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
    # Titik pengantaran selalu berada pada baris paling bawah.
    delivery_end = config.width - 1 if config.delivery_end is None else config.delivery_end
    goals = [(x, config.height - 1) for x in range(config.delivery_start, delivery_end + 1)]
    return Layout(
        width=config.width,
        height=config.height,
        shelves=shelves,
        goals=goals,
    )


def to_rware_layout(layout: Layout) -> str:
    """Ubah layout menjadi peta RWARE; g selalu di baris bawah."""
    cells = [["." for _ in range(layout.width)] for _ in range(layout.height)]
    for x, y in layout.shelves:
        cells[y][x] = "x"
    for x, y in layout.goals:
        cells[y][x] = "g"
    return "\n".join("".join(row) for row in cells)
