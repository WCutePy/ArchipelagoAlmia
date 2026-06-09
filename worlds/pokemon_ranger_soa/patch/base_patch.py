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
    EVENTRECT_PATCHES = {}
    FIELD_MAP_PATCHES = {}

    """School gate"""
    EVENTRECT_PATCHES |= {
        # school gate top
        # PUSH 36		; @29 -> PUSH 14
        "EventRect001104": [
            (29 * 4, 0x00_0E_00_10),
        ],  # TODO fix bug
        # school gate bottom, EventRect001100
        # PUSH 36		; @80 -> PUSH 14
        "EventRect001100": [
            (80 * 4, 0x00_0E_00_10),
        ],  # TODO fix bug
    }

    """Mission 2"""
    """Patches that after destroying the red gigaremo 50495488
    Instead of checking for event variable 0 to be 7,
    to check for any variable 7 or below. This allows
    going out of sequence and not triggering events in
    m006_002, preventing the game from hard softlocking itself,
    even when events in m006_002 are performed later.
    This makes m006_002 optional.
    """
    FIELD_MAP_PATCHES |= {
        # field / map
        # IS_EQ 		; @254 -> IS_LE
        "m006_001": [
            (254 * 4, 0x00_10_00_16)
        ],
    }

    """mission 3 forest fire stuff"""
    EVENTRECT_PATCHES |= {
        # vientown -> school road, EventRect004101
        # 	JZ loc_35		; @30 -> JMP loc_44
        "EventRect004101": [
            (0x78, 0x000D0008),
        ],
        # vientown -> beach, EventRect004102
        # JZ loc_43		; @38 -> JZ loc_52
        "EventRect004102": [
            (0x98, 0x000D0208),
        ],
        # vientown -> chicole path, EventRect004103
        # JZ loc_35		; @30 -> JZ loc_53
        "EventRect004103": [
            (0x78, 0x00160208),
        ],
        # vien forest -> vientown block during mission 3, EventRect009106
        # JZ loc_71 -> JZ loc_87; @66
        "EventRect009106": [
            (0x108, 0x00140208),
        ],
    }

    for eventrect, writes in EVENTRECT_PATCHES.items():
        base_num = eventrect.strip("EventRect")[0:3]
        file_name = f"/data/Script/field/eventrect/er{base_num}/{eventrect}.fsb"
        patch_script(rom, file_name, writes)
