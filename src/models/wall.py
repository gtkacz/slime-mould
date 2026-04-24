from dataclasses import dataclass

from src.enums.directions import Direction


@dataclass(frozen=True)
class Wall:
    """A wall blocking the Hamiltonian path."""

    direction: Direction
