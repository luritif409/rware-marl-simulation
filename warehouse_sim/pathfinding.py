from __future__ import annotations

from collections import deque

from .models import Position


def neighbors(pos: Position, width: int, height: int) -> list[Position]:
    x, y = pos
    result = []
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        nxt = (x + dx, y + dy)
        if 0 <= nxt[0] < width and 0 <= nxt[1] < height:
            result.append(nxt)
    return result


def shortest_path(
    start: Position,
    goal: Position,
    width: int,
    height: int,
    blocked: set[Position],
) -> list[Position]:
    """BFS untuk grid berbobot seragam; hasil mencakup start dan goal."""
    if start == goal:
        return [start]
    queue = deque([start])
    parent: dict[Position, Position | None] = {start: None}
    while queue:
        current = queue.popleft()
        for nxt in neighbors(current, width, height):
            if nxt in blocked or nxt in parent:
                continue
            parent[nxt] = current
            if nxt == goal:
                path = [goal]
                node = goal
                while parent[node] is not None:
                    node = parent[node]  # type: ignore[assignment]
                    path.append(node)
                return list(reversed(path))
            queue.append(nxt)
    return []


def path_distance(path: list[Position]) -> int:
    return max(0, len(path) - 1) if path else 10**9
