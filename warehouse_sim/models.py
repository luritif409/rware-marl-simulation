from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

Position = tuple[int, int]


class RobotState(str, Enum):
    IDLE = "idle"
    TO_SHELF = "menuju_rak"
    TO_GOAL = "menuju_pengantaran"
    TO_RETURN = "mengembalikan_rak"


@dataclass
class Layout:
    width: int
    height: int
    shelves: list[Position]
    goals: list[Position]


@dataclass
class RunResult:
    policy: str
    seed: int
    steps_executed: int
    orders_total: int
    orders_completed: int
    completion_times: list[int]
    blocked_steps: int
    distance_travelled: int
    history: list[dict] = field(default_factory=list)

    @property
    def mean_completion_time(self) -> float | None:
        if not self.completion_times:
            return None
        return sum(self.completion_times) / len(self.completion_times)

    @property
    def throughput(self) -> float:
        if self.steps_executed == 0:
            return 0.0
        return self.orders_completed / self.steps_executed

    def to_summary(self) -> dict:
        return {
            "Kebijakan": self.policy,
            "Seed": self.seed,
            "Langkah simulasi": self.steps_executed,
            "Pesanan selesai": self.orders_completed,
            "Total pesanan": self.orders_total,
            "Rata-rata waktu selesai": self.mean_completion_time,
            "Waktu selesai per pesanan": ";".join(map(str, self.completion_times)),
            "Langkah terhambat": self.blocked_steps,
            "Jarak tempuh": self.distance_travelled,
            "Throughput": self.throughput,
        }
