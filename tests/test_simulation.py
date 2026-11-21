from warehouse_sim import SimulationConfig
from warehouse_sim.layout import generate_layout
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


def test_layout_is_deterministic():
    config = small_config()
    first = generate_layout(config, 7)
    second = generate_layout(config, 7)
    assert first.shelves == second.shelves
    assert first.robot_starts == second.robot_starts


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
