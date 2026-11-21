from warehouse_sim import SimulationConfig
from warehouse_sim.layout import generate_layout
from warehouse_sim.simulation import POLICIES, run_simulation
from warehouse_sim.visualization import sample_history, warehouse_animation


def animation_config() -> SimulationConfig:
    return SimulationConfig(
        width=9,
        height=8,
        n_shelves=6,
        n_robots=2,
        n_orders=5,
        max_steps=300,
        repetitions=1,
        seed=7,
    )


def test_both_policies_have_complete_animation_and_controls():
    config = animation_config()
    layout = generate_layout(config, config.seed)
    for policy in POLICIES:
        result = run_simulation(config, policy, keep_history=True)
        figure, stride = warehouse_animation(layout, result.history, policy)

        assert stride == 1
        assert figure.frames
        assert figure.frames[0].name == "0"
        assert figure.frames[-1].name == str(result.steps_executed)
        assert figure.frames[-1].layout.title.text.endswith(
            f"pesanan selesai {result.orders_completed}"
        )
        assert {button.label for button in figure.layout.updatemenus[0].buttons} == {
            "Play", "Pause"
        }
        assert {button.label for button in figure.layout.updatemenus[1].buttons} == {
            "Lambat", "Normal", "Cepat"
        }
        assert len(figure.layout.sliders[0].steps) == len(figure.frames)


def test_sampling_keeps_endpoints_and_does_not_change_metrics():
    config = animation_config()
    result = run_simulation(config, POLICIES[0], keep_history=True)
    summary_before = result.to_summary().copy()
    sampled, stride = sample_history(result.history, max_frames=10)
    figure, figure_stride = warehouse_animation(
        generate_layout(config, config.seed), result.history, POLICIES[0], max_frames=10
    )

    assert stride > 1
    assert figure_stride == stride
    assert 1 < len(sampled) <= 10
    assert sampled[0]["step"] == 0
    assert sampled[-1]["step"] == result.steps_executed
    assert figure.frames[-1].name == str(result.steps_executed)
    assert result.to_summary() == summary_before
    assert len(result.history) == result.steps_executed + 1


def test_long_history_stays_within_frame_limit():
    history = [{"step": step} for step in range(20_001)]
    sampled, stride = sample_history(history)

    assert stride > 1
    assert len(sampled) <= 300
    assert sampled[0]["step"] == 0
    assert sampled[-1]["step"] == 20_000
