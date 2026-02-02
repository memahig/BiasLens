from __future__ import annotations

from typing import Any, Dict

from .pass_a import validate_pass_a_pack
from .pass_b import validate_pass_b_pack


def validate_pass_a_only(pack: Dict[str, Any]) -> None:
    validate_pass_a_pack(pack)


def validate_full_pack(pack: Dict[str, Any]) -> None:
    eids = validate_pass_a_pack(pack)
    validate_pass_b_pack(pack, eids)
