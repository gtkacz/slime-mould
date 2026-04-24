from dataclasses import dataclass

from src.enums.directions import Direction
from src.models.cell import Cell


@dataclass
class PathCell:
    cell: Cell
    direction_in: Direction
    direction_out: Direction

    def __post_init__(self) -> None:
        if not self.cell.can_pass_from(self.direction_in):
            raise ValueError(f"Path cannot go into cell {self.cell} through {self.direction_in}.")

        if not self.cell.can_pass_from(self.direction_out):
            raise ValueError(f"Path cannot go into cell {self.cell} through {self.direction_out}.")
