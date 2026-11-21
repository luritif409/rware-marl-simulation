from __future__ import annotations

import random
from dataclasses import replace

from .config import SimulationConfig
from .layout import generate_layout
from .models import Order, Robot, RobotState, RunResult
from .pathfinding import neighbors, shortest_path
from .policies import choose_assignment

POLICIES = ("Baseline", "Kontribusi usulan")


def _make_orders(config: SimulationConfig, layout, seed: int) -> list[Order]:
    rng = random.Random(seed + 99_991)
    orders = []
    for order_id in range(1, config.n_orders + 1):
        shelf = rng.choice(layout.shelves)
        orders.append(
            Order(
                order_id=order_id,
                shelf=shelf,
                pickup=layout.pickups[shelf],
            )
        )
    return orders


def _goal_for_robot(robot: Robot, layout, robots: list[Robot]) -> tuple[int, int]:
    occupied_by_others = {
        other.position for other in robots if other.robot_id != robot.robot_id
    }
    reserved_by_others = {
        other.target_goal
        for other in robots
        if other.robot_id != robot.robot_id and other.target_goal is not None
    }
    available_goals = [
        goal
        for goal in layout.goals
        if goal not in occupied_by_others and goal not in reserved_by_others
    ]
    candidates = available_goals or layout.goals
    return min(
        candidates,
        key=lambda goal: abs(goal[0] - robot.position[0]) + abs(goal[1] - robot.position[1]),
    )


def _record_frame(step: int, robots: list[Robot], orders: list[Order]) -> dict:
    return {
        "step": step,
        "robots": [
            {
                "robot_id": robot.robot_id,
                "x": robot.position[0],
                "y": robot.position[1],
                "state": robot.state.value,
                "order_id": robot.order_id,
            }
            for robot in robots
        ],
        "completed": sum(order.completed_at is not None for order in orders),
    }


def run_simulation(
    config: SimulationConfig,
    policy: str,
    seed: int | None = None,
    keep_history: bool = False,
) -> RunResult:
    config.validate()
    if policy not in POLICIES:
        raise ValueError(f"Kebijakan tidak dikenal: {policy}")
    actual_seed = config.seed if seed is None else seed
    layout = generate_layout(config, actual_seed)
    orders = _make_orders(config, layout, actual_seed)
    robots = [
        Robot(robot_id=index + 1, position=position)
        for index, position in enumerate(layout.robot_starts)
    ]
    history = [_record_frame(0, robots, orders)] if keep_history else []
    steps_executed = 0

    for step in range(1, config.max_steps + 1):
        steps_executed = step

        # Penugasan dilakukan berurutan menurut ID robot agar deterministik.
        pending = [order for order in orders if order.assigned_robot is None]
        for robot in robots:
            if robot.state != RobotState.IDLE or not pending:
                continue
            selected = choose_assignment(
                robot,
                pending,
                robots,
                layout,
                policy,
                config.congestion_weight,
                config.congestion_radius,
            )
            if selected is not None:
                selected.assigned_robot = robot.robot_id
                selected.assigned_at = step
                robot.order_id = selected.order_id
                robot.state = RobotState.TO_SHELF
                robot.route = shortest_path(
                    robot.position,
                    selected.pickup,
                    layout.width,
                    layout.height,
                    layout.blocked_cells,
                )
                pending.remove(selected)

        orders_by_id = {order.order_id: order for order in orders}
        proposals: dict[int, tuple[int, int]] = {}
        all_positions = {robot.position for robot in robots}
        for robot in robots:
            if robot.state == RobotState.IDLE or robot.order_id is None:
                continue
            order = orders_by_id[robot.order_id]
            target = (
                order.pickup
                if robot.state == RobotState.TO_SHELF
                else robot.target_goal or _goal_for_robot(robot, layout, robots)
            )
            path = robot.route
            if not path or path[0] != robot.position or path[-1] != target:
                path = shortest_path(
                    robot.position,
                    target,
                    layout.width,
                    layout.height,
                    layout.blocked_cells,
                )
                robot.route = path
            if len(path) > 1:
                idle_positions = {
                    other.position
                    for other in robots
                    if other.robot_id != robot.robot_id and other.state == RobotState.IDLE
                }
                if path[1] in idle_positions:
                    alternative = shortest_path(
                        robot.position,
                        target,
                        layout.width,
                        layout.height,
                        layout.blocked_cells | idle_positions,
                    )
                    if alternative:
                        path = alternative
                        robot.route = alternative
            proposal = path[1] if len(path) > 1 else robot.position
            if robot.consecutive_blocked >= 5:
                escape_cells = [
                    cell
                    for cell in neighbors(robot.position, layout.width, layout.height)
                    if cell not in layout.blocked_cells and cell not in all_positions
                ]
                if escape_cells:
                    proposal = escape_cells[(step + robot.robot_id) % len(escape_cells)]
            proposals[robot.robot_id] = proposal

        # Konflik: dua robot menuju sel sama, bertukar posisi, atau menuju sel robot diam.
        current = {robot.robot_id: robot.position for robot in robots}
        occupied = {robot.position: robot.robot_id for robot in robots}

        # Jika dua robot saling bertukar sel, salah satunya mengambil langkah
        # samping ke sel bebas. Ini memecah deadlock pada lorong dua arah.
        forced_wait: set[int] = set()
        processed_swaps: set[frozenset[int]] = set()
        for robot_id, target in list(proposals.items()):
            other_id = occupied.get(target)
            if other_id is None or other_id == robot_id:
                continue
            pair = frozenset((robot_id, other_id))
            if pair in processed_swaps:
                continue
            if proposals.get(other_id) != current[robot_id]:
                continue
            processed_swaps.add(pair)
            yielder = min(pair, key=lambda rid: (rid - 1 - step) % len(robots))
            waiter = other_id if yielder == robot_id else robot_id
            original_target = proposals[yielder]
            unavailable = layout.blocked_cells | set(occupied) | set(proposals.values())
            side_cells = [
                cell
                for cell in neighbors(current[yielder], layout.width, layout.height)
                if cell not in unavailable
            ]
            other_position = current[waiter]
            if current[yielder][0] == other_position[0]:
                lateral = [cell for cell in side_cells if cell[0] != current[yielder][0]]
            else:
                lateral = [cell for cell in side_cells if cell[1] != current[yielder][1]]
            if lateral:
                side_cells = lateral
            if side_cells:
                proposals[yielder] = min(
                    side_cells,
                    key=lambda cell: abs(cell[0] - original_target[0])
                    + abs(cell[1] - original_target[1]),
                )
                proposals[waiter] = current[waiter]
                forced_wait.add(waiter)

        contenders: dict[tuple[int, int], list[int]] = {}
        for robot_id, target in proposals.items():
            contenders.setdefault(target, []).append(robot_id)

        # Prioritas bergilir mencegah robot ber-ID kecil selalu menang.
        winners: dict[tuple[int, int], int] = {}
        for target, robot_ids in contenders.items():
            winners[target] = min(
                robot_ids,
                key=lambda robot_id: (robot_id - 1 - step) % len(robots),
            )

        accepted: set[int] = set()
        for robot in robots:
            if robot.robot_id not in proposals:
                continue
            target = proposals[robot.robot_id]
            blocked = winners[target] != robot.robot_id
            occupant = occupied.get(target)
            if occupant is not None and occupant != robot.robot_id:
                occupant_target = proposals.get(occupant, current[occupant])
                if occupant_target == current[robot.robot_id] or occupant_target == current[occupant]:
                    blocked = True
            if blocked:
                robot.blocked_steps += 1
                robot.consecutive_blocked += 1
            else:
                accepted.add(robot.robot_id)

        # Pengamanan tambahan untuk perpindahan menuju sel robot yang akhirnya tertahan.
        changed = True
        while changed:
            changed = False
            for robot_id in list(accepted):
                target = proposals[robot_id]
                occupant = occupied.get(target)
                if occupant is not None and occupant != robot_id and occupant not in accepted:
                    accepted.remove(robot_id)
                    robots[robot_id - 1].blocked_steps += 1
                    robots[robot_id - 1].consecutive_blocked += 1
                    changed = True

        for robot in robots:
            if robot.robot_id in forced_wait:
                robot.blocked_steps += 1
                robot.consecutive_blocked += 1
            if robot.robot_id in accepted:
                target = proposals[robot.robot_id]
                if target != robot.position:
                    robot.position = target
                    robot.distance += 1
                    robot.consecutive_blocked = 0
                    if len(robot.route) > 1 and robot.route[1] == target:
                        robot.route.pop(0)
                    else:
                        # Gerak samping pemecah deadlock; rute akan dibuat ulang.
                        robot.route = []

        # Perubahan status setelah gerakan.
        for robot in robots:
            if robot.order_id is None:
                continue
            order = orders_by_id[robot.order_id]
            if robot.state == RobotState.TO_SHELF and robot.position == order.pickup:
                robot.state = RobotState.TO_GOAL
                robot.target_goal = _goal_for_robot(robot, layout, robots)
                robot.route = shortest_path(
                    robot.position,
                    robot.target_goal,
                    layout.width,
                    layout.height,
                    layout.blocked_cells,
                )
            elif (
                robot.state == RobotState.TO_GOAL
                and robot.position in layout.goals
            ):
                order.completed_at = step
                robot.state = RobotState.IDLE
                robot.order_id = None
                robot.target_goal = None
                robot.route = []

        if keep_history:
            history.append(_record_frame(step, robots, orders))
        if all(order.completed_at is not None for order in orders):
            break

    completion_times = [
        order.completed_at - order.created_at
        for order in orders
        if order.completed_at is not None
    ]
    return RunResult(
        policy=policy,
        seed=actual_seed,
        steps_executed=steps_executed,
        orders_total=len(orders),
        orders_completed=len(completion_times),
        completion_times=completion_times,
        blocked_steps=sum(robot.blocked_steps for robot in robots),
        distance_travelled=sum(robot.distance for robot in robots),
        history=history,
    )


def compare_policies(config: SimulationConfig) -> tuple[list[RunResult], object]:
    """Menjalankan kedua kebijakan pada seed dan skenario yang identik."""
    results: list[RunResult] = []
    for repetition in range(config.repetitions):
        seed = config.seed + repetition
        for policy in POLICIES:
            results.append(run_simulation(config, policy, seed=seed))
    layout = generate_layout(config, config.seed)
    return results, layout


def demo_results(config: SimulationConfig) -> dict[str, RunResult]:
    """Satu pengulangan dengan riwayat posisi untuk visualisasi."""
    demo_config = replace(config, repetitions=1)
    return {
        policy: run_simulation(demo_config, policy, seed=config.seed, keep_history=True)
        for policy in POLICIES
    }
