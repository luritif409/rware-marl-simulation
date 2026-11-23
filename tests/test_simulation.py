import pytest

from warehouse_sim import SimulationConfig
from warehouse_sim.config import WAREHOUSE_SIZES
from warehouse_sim.layout import generate_layout, to_rware_layout
from warehouse_sim.simulation import POLICIES, compare_policies, run_simulation


def small_config(**changes):
    values = dict(
        width=9,
        height=8,
        n_shelves=6,
        n_robots=2,
        n_orders=5,
        max_steps=300,
        congestion_weight=2.0,
        congestion_radius=2,
        repetitions=2,
        seed=7,
    )
    values.update(changes)
    return SimulationConfig(**values)


def test_warehouse_size_presets_match_rware_dimensions():
    assert WAREHOUSE_SIZES == {
        "Tiny": (10, 11),
        "Small": (10, 20),
        "Medium": (16, 20),
        "Large": (16, 29),
    }
    assert (SimulationConfig().width, SimulationConfig().height) == WAREHOUSE_SIZES["Tiny"]


def test_layout_is_deterministic():
    config = small_config()
    first = generate_layout(config, 7)
    second = generate_layout(config, 7)
    assert first.shelves == second.shelves
    assert first.goals == second.goals


def test_full_shelf_capacity_is_larger_than_default():
    config = small_config(width=12, height=10, n_shelves=42)
    layout = generate_layout(config, config.seed)
    assert len(layout.shelves) == 42
    assert all(x % 3 != 0 for x, _ in layout.shelves)
    assert all(y < config.height - 3 for _, y in layout.shelves)


def test_rware_episode_is_paired_and_returns_shelves():
    config = small_config()
    baseline = run_simulation(config, POLICIES[0], keep_history=True)
    proposed = run_simulation(config, POLICIES[1], keep_history=True)
    assert baseline.history[0] == proposed.history[0]
    assert baseline.orders_completed == config.n_orders
    assert any(
        robot["state"] == "mengembalikan_rak"
        for frame in baseline.history for robot in frame["robots"]
    )
    assert any(
        shelf["carried"] for frame in baseline.history for shelf in frame["shelves"]
    )
    rware_rows = to_rware_layout(generate_layout(config, config.seed)).splitlines()
    assert "g" not in "".join(rware_rows[:-1])
    assert "g" in rware_rows[-1]


def test_request_queue_size_controls_initial_rware_requests():
    config = small_config(request_queue_size=1)
    result = run_simulation(config, POLICIES[0], keep_history=True)
    assert sum(shelf["requested"] for shelf in result.history[0]["shelves"]) == 1


@pytest.mark.parametrize(
    ("start", "end", "expected_goals"),
    [
        (0, None, [(x, 7) for x in range(9)]),
        (2, 4, [(x, 7) for x in range(2, 5)]),
        (3, 3, [(3, 7)]),
    ],
)
def test_delivery_columns_stay_on_bottom_row(start, end, expected_goals):
    config = small_config(delivery_start=start, delivery_end=end)
    layout = generate_layout(config, config.seed)
    assert layout.goals == expected_goals


@pytest.mark.parametrize(("start", "end"), [(-1, 2), (4, 3), (0, 9)])
def test_invalid_delivery_columns_are_rejected(start, end):
    with pytest.raises(ValueError, match="Rentang kolom pengantaran"):
        small_config(delivery_start=start, delivery_end=end).validate()


def test_single_bottom_delivery_point_remains_usable():
    config = small_config(n_robots=4, n_orders=5, delivery_start=4, delivery_end=4)
    for policy in POLICIES:
        result = run_simulation(config, policy)
        assert result.orders_completed == config.n_orders


def test_both_policies_complete_small_case():
    config = small_config()
    for policy in POLICIES:
        result = run_simulation(config, policy)
        assert result.orders_completed == config.n_orders
        assert result.distance_travelled > 0
        assert result.mean_completion_time is not None


def test_comparison_is_paired_by_seed():
    config = small_config(repetitions=3)
    results, _ = compare_policies(config)
    assert len(results) == 6
    assert [result.seed for result in results] == [7, 7, 8, 8, 9, 9]


def test_history_can_be_recorded():
    result = run_simulation(small_config(), "Baseline", keep_history=True)
    assert result.history[0]["step"] == 0
    assert result.history[-1]["completed"] == result.orders_completed
