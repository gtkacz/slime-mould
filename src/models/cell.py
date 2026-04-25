from collections.abc import Sequence
from dataclasses import dataclass

from src.enums.directions import Direction
from src.models.wall import Wall


@dataclass
class Cell:
    """A cell on a bidimensional grid."""

    x: int
    y: int
    waypoint_value: int
    walls: Sequence[Wall]

    def __post_init__(self) -> None:
        self.blocked_directions = tuple(wall.direction for wall in self.walls)

    def can_pass_from(self, direction: Direction) -> bool:
        """Checks if the Hamiltonian path can pass through this cell from the intended direction.

        Args:
            direction (Direction): The direction the path will move through.

        Returns:
            bool: Whether or not the path can pass through.
        """
        return direction not in self.blocked_directions

    def __str__(self) -> str:
        return "." if self.waypoint_value == 0 else str(self.waypoint_value)

    def walls_to_representation(self) -> str:
        bits = 0

        if Direction.TOP in self.blocked_directions:
            bits |= 8

        if Direction.RIGHT in self.blocked_directions:
            bits |= 4

        if Direction.BOTTOM in self.blocked_directions:
            bits |= 2

        if Direction.LEFT in self.blocked_directions:
            bits |= 1

        # Format the integer as an uppercase Hexadecimal string
        return f"{bits:X}"

    @classmethod
    def walls_from_representation(cls, value: str) -> tuple[Wall, ...]:
        """Reconstructs a Cell from a hexadecimal character representation.

        Args:
            value (str): A hexadecimal string representing blocked directions.

        Returns:
            tuple[Wall, ...]: The reconstructed walls for the represented cell.
        """
        bits = int(value, 16)

        blocked_directions = []

        if bits & 8:
            blocked_directions.append(Direction.TOP)

        if bits & 4:
            blocked_directions.append(Direction.RIGHT)

        if bits & 2:
            blocked_directions.append(Direction.BOTTOM)

        if bits & 1:
            blocked_directions.append(Direction.LEFT)

        return tuple(Wall(direction) for direction in blocked_directions)
