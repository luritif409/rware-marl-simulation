from __future__ import annotations

from dataclasses import asdict, dataclass


WAREHOUSE_SIZES = {
    "Tiny": (10, 11),
    "Small": (10, 20),
    "Medium": (16, 20),
    "Large": (16, 29),
}


@dataclass(frozen=True)
class SimulationConfig:
    width: int = 10
    height: int = 11
    n_shelves: int = 18
    n_robots: int = 4
    request_queue_size: int | None = None
    n_orders: int = 20
    max_steps: int = 1000
    congestion_weight: float = 2.0
    congestion_radius: int = 2
    repetitions: int = 10
    seed: int = 42
    delivery_start: int = 0
    delivery_end: int | None = None

    def validate(self) -> None:
        if self.width < 8 or self.height < 8:
            raise ValueError("Ukuran gudang minimum adalah 8 × 8.")
        if self.n_shelves < 2:
            raise ValueError("RWARE memerlukan minimal 2 rak agar antrean permintaan dapat diperbarui.")
        if self.n_robots < 1:
            raise ValueError("Jumlah robot minimal 1.")
        delivery_end = self.width - 1 if self.delivery_end is None else self.delivery_end
        if not 0 <= self.delivery_start <= delivery_end < self.width:
            raise ValueError("Rentang kolom pengantaran harus berada dalam lebar gudang.")
        if self.n_robots > self.width:
            raise ValueError(f"Jumlah robot terlalu besar. Maksimum {self.width} untuk lebar gudang ini.")
        requests = min(self.n_robots, self.n_shelves - 1) if self.request_queue_size is None else self.request_queue_size
        if not 1 <= requests < self.n_shelves:
            raise ValueError("Jumlah rak diminta serentak (R) harus antara 1 dan jumlah rak dikurangi 1.")
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
