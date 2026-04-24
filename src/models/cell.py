from collections.abc import Sequence
from dataclasses import dataclass

from src.enums.directions import Direction
from src.models.wall import Wall


@dataclass
class Cell:
    """A cell on a bidimensional grid."""

    x: int
    y: int
    value: int
    walls: Sequence[Wall]

    def __post_init__(self) -> None:
        self._blocked_directions = (wall.direction for wall in self.walls)

    def can_pass_from(self, direction: Direction) -> bool:
        """Checks if the Hamiltonian path can pass through this cell from the intended direction.

        Args:
            direction (Direction): The direction the path will move through.

        Returns:
            bool: Whether or not the path can pass through.
        """
        return direction not in self._blocked_directions
