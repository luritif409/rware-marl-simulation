from __future__ import annotations

from .models import Position


def congestion_score(
    path: list[Position], robot_positions: list[Position], radius: int
) -> float:
    if not path:
        return float("inf")
    score = 0.0
    # Posisi awal robot tidak dihitung; hanya jalur yang akan dilalui.
    for cell in path[1:]:
        for other in robot_positions:
            distance = abs(cell[0] - other[0]) + abs(cell[1] - other[1])
            if distance <= radius:
                score += (radius + 1 - distance) / (radius + 1)
    return score


