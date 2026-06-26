from __future__ import annotations

import struct
from typing import (
    TYPE_CHECKING,
)

from settings import get_settings
from worlds.Files import APProcedurePatch, APTokenMixin, APTokenTypes

if TYPE_CHECKING:
    from .world import PokemonTrozei


ARM9_ROM_OFFSET = 0x4000


class PokemonLinkProcedurePatch(APProcedurePatch, APTokenMixin):
    game = "Pokemon Trozei"
    hash = "5af68afc469ee54adc3721d9d8913904"
    patch_file_ending = ".applink"
    result_file_ending = ".nds"

    procedure = [
        ("apply_tokens", ["token_data.bin"])
    ]

    @classmethod
    def get_source_data(cls) -> bytes:
        with open(get_settings().pokemon_trozei_settings.link_rom_file, "rb") as infile:
            base_rom_bytes = bytes(infile.read())

        return base_rom_bytes


def write_tokens(world: "PokemonTrozei", patch: PokemonLinkProcedurePatch) -> None:

    addresses = []

    addresses += [
        ARM9_ROM_OFFSET + 0x56050,
        ARM9_ROM_OFFSET + 0x55F8C,
    ]

    for address in addresses:
        patch.write_token(
            APTokenTypes.WRITE,
            address,
            struct.pack("<I", 0xE3A00000),
        )

    patch.write_file("token_data.bin", patch.get_token_binary())