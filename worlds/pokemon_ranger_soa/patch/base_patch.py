from typing import TYPE_CHECKING

from ..apnds.rom import Rom
from ..apnds.narc import Narc

if TYPE_CHECKING:
    from ..rom import PokemonRSOAPatch


def patch(
    rom: Rom,
    world_package: str,
    bw_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:
    return
