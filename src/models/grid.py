from functools import cached_property
from collections.abc import Sequence
from dataclasses import dataclass

from src.models.cell import Cell


@dataclass(frozen=True)
class Grid:
    n: int
    cells: Sequence[Cell]

    @cached_property
    def cells_representation(self) -> tuple[str, ...]:
        pass

    @cached_property
    def walls_representation(self) -> tuple[str, ...]:
        pass
