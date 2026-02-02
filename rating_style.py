# rating_style.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class RatingStyle:
    star: str = "⭐"
    circle_map: dict[int, str] = None

    def __post_init__(self):
        if self.circle_map is None:
            object.__setattr__(self, "circle_map", {
                1: "🔴",
                2: "🟠",
                3: "🟡",
                4: "🟢",
                5: "🔵",
            })

DEFAULT_STYLE = RatingStyle()


def clamp_rating(r: int) -> int:
    return max(1, min(5, int(r)))


def render_rating(rating: int, style: RatingStyle = DEFAULT_STYLE) -> str:
    """
    Renders rating as:
      ⭐⭐⭐⭐ 🟢
    """
    r = clamp_rating(rating)
    stars = style.star * r
    circle = style.circle_map.get(r, "")
    return f"{stars} {circle}".strip()
