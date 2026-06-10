import struct
from collections import defaultdict
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
    """
    Patch 4 byte instructions in scripts with a set of 4 byte writes.
    """
    data = bytearray(rom.files[file_name])

    for offset, instruction in writes:
        offset = offset * 4
        struct.pack_into("<I", data, offset, instruction)

    rom.files[file_name] = bytes(data)


def patch(
    rom: Rom,
    world_package: str,
    bw_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:
    EVENTRECT_PATCHES = defaultdict(list)
    FIELD_MAP_PATCHES = defaultdict(list)
    CHAPTER_PATCHES = defaultdict(list)

    """School gate"""
    EVENTRECT_PATCHES |= {
        # school gate top
        # PUSH 36		; @29 -> PUSH 14
        "EventRect001104": [
            (29, 0x00_0E_00_10),
        ],  # TODO fix bug
        # school gate bottom, EventRect001100
        # PUSH 36		; @80 -> PUSH 14
        "EventRect001100": [
            (80, 0x00_0E_00_10),
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
    FIELD_MAP_PATCHES["m006_001"] += [
        # IS_EQ 		; @254 -> IS_LE
        (254, 0x00_10_00_16)
    ]

    """mission 3 forest backtracking"""
    EVENTRECT_PATCHES |= {
        # vientown -> school road, EventRect004101
        # 	JZ loc_35		; @30 -> JMP loc_44
        "EventRect004101": [
            (30, 0x000D0008),
        ],
        # vientown -> beach, EventRect004102
        # JZ loc_43		; @38 -> JZ loc_52
        "EventRect004102": [
            (38, 0x000D0208),
        ],
        # vientown -> chicole path, EventRect004103
        # JZ loc_35		; @30 -> JZ loc_53
        "EventRect004103": [
            (30, 0x00160208),
        ],
        # vien forest -> vientown block during mission 3, EventRect009106
        # JZ loc_71 -> JZ loc_87; @66
        "EventRect009106": [
            (66, 0x00140208),
        ],
    }

    """mission 3 mimi happiny"""

    CHAPTER_PATCHES["c026"] += [
        # PUSH32 17018892		; @5068 -> PUSH 211
        (5068, 0X00_D3_00_10),
        (5069, 0X0),
        # SYSCALL 2, 142, 1		;syscall_2_142 @5070 -> SYSCALL 2, 141, 1
        (5070, 0x08_8D_01_01),
        # IS_EQ 		; @5073 -> IS_GE
        (5073, 0x0),
        # JZ loc_5113		; @5074 -> JZ loc_5203
        (5074, 0x0),

        # PUSH 3		; @5206 -> PUSH 1 ??
        (5206, 0x0)
    ]

    """mission 3 blastoise"""
    """A patch to allow any blastoise to be usable to complete the 
    forest fire, rather than specifically needing to have 17018880 in your party."""
    # TODO modify this if species field moves become random
    CHAPTER_PATCHES["c026"] += [
        # PUSH32 17018880		; @4429 -> PUSH 5 and NOP 0
        (4429 * 4, 0x00_05_00_10),
        (4430 * 4, 0x0),
        # SYSCALL 2, 142, 1		;syscall_2_142 @4431 -> SYSCALL 2, 141, 1
        (4431 * 4, 0x08_8D_01_01),
    ]


    for eventrect, writes in EVENTRECT_PATCHES.items():
        base_num = eventrect.strip("EventRect")[0:3]
        file_name = f"/data/Script/field/eventrect/er{base_num}/{eventrect}.fsb"
        patch_script(rom, file_name, writes)

    for map_name, writes in FIELD_MAP_PATCHES.items():
        area = map_name.split("_")[0]
        file_name = f"/data/Script/field/map/{area}/{map_name}.fsb"
        patch_script(rom, file_name, writes)

    for chapter, writes in CHAPTER_PATCHES.items():
        file_name = f"/data/Script/chapter/{chapter}.fsb"
        patch_script(rom, file_name, writes)
