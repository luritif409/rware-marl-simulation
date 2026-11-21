from __future__ import annotations

from .models import Layout, Order, Position, Robot
from .pathfinding import path_distance, shortest_path


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


def choose_assignment(
    robot: Robot,
    pending_orders: list[Order],
    robots: list[Robot],
    layout: Layout,
    policy: str,
    congestion_weight: float,
    congestion_radius: int,
) -> Order | None:
    best_order: Order | None = None
    best_score = float("inf")
    robot_positions = [r.position for r in robots if r.robot_id != robot.robot_id]
    for order in pending_orders:
        path = shortest_path(
            robot.position,
            order.pickup,
            layout.width,
            layout.height,
            layout.blocked_cells,
        )
        distance = path_distance(path)
        score = float(distance)
        if policy == "Kontribusi usulan":
            score += congestion_weight * congestion_score(
                path, robot_positions, congestion_radius
            )
        tie_break = order.order_id / 1_000_000
        score += tie_break
        if score < best_score:
            best_score = score
            best_order = order
    return best_order
