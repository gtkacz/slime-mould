from collections.abc import Sequence
from dataclasses import dataclass

from src.models.cell import Cell


@dataclass(frozen=True)
class Grid:
    n: int
    cells: Sequence[Cell]
