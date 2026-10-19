"""Bellek içi ses klibi. Diske yazılmaz."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PcmClip:
    samples: object  # numpy.ndarray float32, shape (n,), -1..1
    sample_rate: int

    @property
    def duration_s(self) -> float:
        n = len(self.samples)  # type: ignore[arg-type]
        return n / self.sample_rate if self.sample_rate else 0.0

    def to_float32(self) -> object:
        return self.samples
