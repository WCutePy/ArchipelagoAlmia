import struct
from typing import TYPE_CHECKING

from ..apnds.rom import Rom
from ..apnds.narc import Narc

if TYPE_CHECKING:
    from ..rom import PokemonRSOAPatch


def patch_script(
    rom: Rom,
    file_name: str,
    writes: list[tuple[int, int]],
) -> None:
    data = bytearray(rom.files[file_name])

    for offset, instruction in writes:
        struct.pack_into("<I", data, offset, instruction)

    rom.files[file_name] = bytes(data)


def patch(
    rom: Rom,
    world_package: str,
    bw_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:

    EVENTRECT_PATCHES = {
        # school gate"""
        # school gate top, EventRect001104
        # JZ loc_35 -> NOP 0; @31
        "EventRect001104": [
            (31 * 4, 0x00000000),
        ],
        # school gate bottom, EventRect001100
        # JZ loc_86 -> NOP 0; @82
        "EventRect001100": [
            (82 * 4, 0x00000000),
        ],
        # mission 3 forest fire stuff
        # vientown -> school road, EventRect004101
        # 	JZ loc_35		; @30 -> JMP loc_44
        "EventRect004101": [
            (0x78, 0x000D0008),
        ],
        # vientown -> beach, EventRect004102
        # JZ loc_43		; @38 -> JMP loc_52
        "EventRect004102": [
            (0x98, 0x000D0008),
        ],
        # vientown -> chicole path, EventRect004103
        # JZ loc_35		; @30 -> JMP loc_53
        "EventRect004103": [
            (0x78, 0x00160008),
        ],
        # vien forest -> vientown block during mission 3, EventRect009106
        # JZ loc_36 -> JMP loc_54; @31
        # JZ loc_71 -> JZ loc_87; @66
        "EventRect009106": [
            (0x7C, 0x00160008),
            (0x108, 0x00140208),
        ],
    }

    for eventrect, writes in EVENTRECT_PATCHES.items():
        base_num = eventrect.strip("EventRect")[0:3]
        file_name = f"/data/Script/field/eventrect/er{base_num}/{eventrect}.fsb"
        patch_script(rom, file_name, writes)
