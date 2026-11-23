"""Heuristic controllers and evaluation on the RWARE environment."""

from __future__ import annotations

from dataclasses import dataclass, replace

from rware.warehouse import Action, Direction, RewardType, Warehouse

from .config import SimulationConfig
from .layout import generate_layout, to_rware_layout
from .models import RobotState, RunResult
from .pathfinding import neighbors, shortest_path
from .policies import congestion_score

POLICIES = ("Baseline", "Kontribusi usulan")


@dataclass
class _Plan:
    shelf_id: int | None = None
    returning: bool = False


def _make_env(config: SimulationConfig, layout) -> Warehouse:
    return Warehouse(
        shelf_columns=3, column_height=4, shelf_rows=1,
        n_agents=config.n_robots, msg_bits=0, sensor_range=1,
        request_queue_size=(min(config.n_robots, config.n_shelves - 1)
                            if config.request_queue_size is None else config.request_queue_size),
        max_inactivity_steps=None, max_steps=config.max_steps,
        reward_type=RewardType.INDIVIDUAL, layout=to_rware_layout(layout),
    )


def _route(env: Warehouse, start, target, loaded: bool, avoid_agents: bool = False):
    carried_ids = {a.carrying_shelf.id for a in env.agents if a.carrying_shelf}
    blocked = (
        {(int(s.x), int(s.y)) for s in env.shelfs if s.id not in carried_ids}
        if loaded else set()
    )
    blocked.discard(start)
    if avoid_agents:
        blocked.update((int(a.x), int(a.y)) for a in env.agents
                       if (int(a.x), int(a.y)) != start)
    height, width = env.grid_size
    if avoid_agents and target in blocked:
        nearby = [
            shortest_path(start, cell, width, height, blocked)
            for cell in neighbors(target, width, height)
            if cell not in blocked
        ]
        reachable = [path for path in nearby if path]
        return min(reachable, key=lambda path: (len(path), path[-1])) if reachable else []
    return shortest_path(start, target, width, height, blocked)


def _move_toward(env: Warehouse, agent, target) -> Action:
    start = (int(agent.x), int(agent.y))
    path = _route(env, start, target, agent.carrying_shelf is not None, avoid_agents=True)
    if len(path) < 2:
        return Action.NOOP
    dx = path[1][0] - start[0]
    dy = path[1][1] - start[1]
    wanted = {(0, -1): Direction.UP, (1, 0): Direction.RIGHT,
              (0, 1): Direction.DOWN, (-1, 0): Direction.LEFT}[(dx, dy)]
    if agent.dir == wanted:
        return Action.FORWARD
    clockwise = (Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT)
    turns = (clockwise.index(wanted) - clockwise.index(agent.dir)) % 4
    return Action.RIGHT if turns in (1, 2) else Action.LEFT


def _assign(env: Warehouse, plans: list[_Plan], policy: str, config: SimulationConfig) -> None:
    claimed = {p.shelf_id for p in plans if p.shelf_id is not None}
    carried = {a.carrying_shelf.id for a in env.agents if a.carrying_shelf}
    for index, agent in enumerate(env.agents):
        if agent.carrying_shelf or plans[index].shelf_id is not None:
            continue
        start = (int(agent.x), int(agent.y))
        others = [(int(a.x), int(a.y)) for a in env.agents if a is not agent]
        candidates = []
        for shelf in env.request_queue:
            if shelf.id in claimed or shelf.id in carried:
                continue
            path = _route(env, start, (int(shelf.x), int(shelf.y)), False)
            if not path:
                continue
            score = float(len(path) - 1)
            if policy == "Kontribusi usulan":
                score += config.congestion_weight * congestion_score(
                    path, others, config.congestion_radius
                )
            candidates.append((score, shelf.id))
        if candidates:
            plans[index].shelf_id = min(candidates)[1]
            claimed.add(plans[index].shelf_id)


def _action_for(env: Warehouse, agent, plan: _Plan, homes) -> Action:
    start = (int(agent.x), int(agent.y))
    if agent.carrying_shelf:
        if plan.returning:
            home = homes[agent.carrying_shelf.id]
            return Action.TOGGLE_LOAD if start == home else _move_toward(env, agent, home)
        paths = [(len(path), tuple(goal)) for goal in env.goals
                 if (path := _route(env, start, tuple(goal), True, avoid_agents=True))]
        return _move_toward(env, agent, min(paths)[1]) if paths else Action.NOOP
    if plan.shelf_id is None:
        return Action.NOOP
    shelf = env.shelfs[plan.shelf_id - 1]
    target = (int(shelf.x), int(shelf.y))
    return Action.TOGGLE_LOAD if start == target else _move_toward(env, agent, target)


def _frame(env: Warehouse, plans: list[_Plan], step: int, completed: int) -> dict:
    requested = {s.id for s in env.request_queue}
    carried = {a.carrying_shelf.id for a in env.agents if a.carrying_shelf}
    return {
        "step": step, "completed": completed,
        "shelves": [{"id": s.id, "x": int(s.x), "y": int(s.y),
                     "requested": s.id in requested, "carried": s.id in carried}
                    for s in env.shelfs],
        "robots": [{
            "robot_id": index + 1, "x": int(a.x), "y": int(a.y),
            "state": (RobotState.TO_RETURN.value if plans[index].returning
                      else RobotState.TO_GOAL.value if a.carrying_shelf
                      else RobotState.TO_SHELF.value if plans[index].shelf_id is not None
                      else RobotState.IDLE.value),
            "order_id": plans[index].shelf_id,
        } for index, a in enumerate(env.agents)],
    }


def run_simulation(config: SimulationConfig, policy: str,
                   seed: int | None = None, keep_history: bool = False) -> RunResult:
    config.validate()
    if policy not in POLICIES:
        raise ValueError(f"Kebijakan tidak dikenal: {policy}")
    actual_seed = config.seed if seed is None else seed
    layout = generate_layout(config, actual_seed)
    env = _make_env(config, layout)
    try:
        env.reset(seed=actual_seed)
        homes = {s.id: (int(s.x), int(s.y)) for s in env.shelfs}
        plans = [_Plan() for _ in env.agents]
        requested_at = {s.id: 0 for s in env.request_queue}
        completion_times: list[int] = []
        blocked_steps = distance_travelled = steps_executed = 0
        history = [_frame(env, plans, 0, 0)] if keep_history else []
        for step in range(1, config.max_steps + 1):
            _assign(env, plans, policy, config)
            before = [(int(a.x), int(a.y)) for a in env.agents]
            actions = [_action_for(env, a, p, homes) for a, p in zip(env.agents, plans)]
            _, rewards, done, truncated, _ = env.step([action.value for action in actions])
            steps_executed = step
            for index, (agent, action, previous) in enumerate(zip(env.agents, actions, before)):
                current = (int(agent.x), int(agent.y))
                distance_travelled += abs(current[0] - previous[0]) + abs(current[1] - previous[1])
                if action == Action.FORWARD and current == previous:
                    blocked_steps += 1
                if rewards[index] > 0:
                    shelf_id = agent.carrying_shelf.id
                    requested_step = requested_at.pop(shelf_id, 0)
                    if len(completion_times) < config.n_orders:
                        completion_times.append(step - requested_step)
                    plans[index].returning = True
                if agent.carrying_shelf is None and plans[index].returning:
                    plans[index] = _Plan()
                elif plans[index].shelf_id is not None and agent.carrying_shelf is None:
                    if plans[index].shelf_id not in {s.id for s in env.request_queue}:
                        plans[index] = _Plan()
            for shelf in env.request_queue:
                requested_at.setdefault(shelf.id, step)
            if keep_history:
                history.append(_frame(env, plans, step, len(completion_times)))
            if len(completion_times) >= config.n_orders or done or truncated:
                break
        return RunResult(
            policy=policy, seed=actual_seed, steps_executed=steps_executed,
            orders_total=config.n_orders, orders_completed=len(completion_times),
            completion_times=completion_times, blocked_steps=blocked_steps,
            distance_travelled=distance_travelled, history=history,
        )
    finally:
        env.close()


def compare_policies(config: SimulationConfig) -> tuple[list[RunResult], object]:
    results = [run_simulation(config, policy, seed=config.seed + repetition)
               for repetition in range(config.repetitions) for policy in POLICIES]
    return results, generate_layout(config, config.seed)


def demo_results(config: SimulationConfig) -> dict[str, RunResult]:
    demo_config = replace(config, repetitions=1)
    return {policy: run_simulation(demo_config, policy, seed=config.seed, keep_history=True)
            for policy in POLICIES}
