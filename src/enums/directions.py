from enum import StrEnum, auto


class Direction(StrEnum):
    """Represents one of the four cardinal directions."""

    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
