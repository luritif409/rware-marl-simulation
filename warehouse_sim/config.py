from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SimulationConfig:
    width: int = 12
    height: int = 10
    n_shelves: int = 18
    n_robots: int = 4
    n_orders: int = 20
    max_steps: int = 1000
    congestion_weight: float = 2.0
    congestion_radius: int = 2
    repetitions: int = 10
    seed: int = 42

    def validate(self) -> None:
        if self.width < 8 or self.height < 8:
            raise ValueError("Ukuran gudang minimum adalah 8 × 8.")
        if self.n_shelves < 1:
            raise ValueError("Jumlah rak minimal 1.")
        if self.n_robots < 1:
            raise ValueError("Jumlah robot minimal 1.")
        if self.n_orders < 1:
            raise ValueError("Jumlah pesanan minimal 1.")
        if self.max_steps < 10:
            raise ValueError("Maksimum langkah minimal 10.")
        if self.congestion_weight < 0:
            raise ValueError("Bobot kepadatan tidak boleh negatif.")
        if self.congestion_radius < 1:
            raise ValueError("Radius kepadatan minimal 1.")
        if self.repetitions < 1:
            raise ValueError("Jumlah pengulangan minimal 1.")

    def to_dict(self) -> dict:
        return asdict(self)
