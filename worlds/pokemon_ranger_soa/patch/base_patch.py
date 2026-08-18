import struct
from collections import defaultdict
from typing import TYPE_CHECKING

from orjson import orjson

from .map_patch import CompactMapData
from ..apnds.rom import Rom
from ..apnds.narc import Narc
from ..data import data

if TYPE_CHECKING:
    from ..rom import PokemonRSOAPatch


def patch_script_in_place_four_bytes(
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


def patch_script_add_doduo(rom: Rom, file_name: str, locations: list[int]):
    data = bytearray(rom.files[file_name])

    jumps = [0x0208]

    code_len = int.from_bytes(data[0:4], "little")
    code_start = 0x20
    code_end = code_start + code_len

    for offset in range(4, 28, 4):
        val = int.from_bytes(data[offset : offset + 4], "little")
        if val == 0:
            continue
        new_val = val + len(locations) * 2
        struct.pack_into("<I", data, offset, new_val)

    for offset in range(code_start, code_end, 4):
        instruction = int.from_bytes(data[offset : offset + 4], "little")

        if (instruction >> 24) != 8:
            continue
        print(f"{offset:08X}: {instruction:08X}")


def list_of_same_patches(change: int, addresses: list[int]) -> list[tuple[int, int]]:
    return [(i, change) for i in addresses]


def patch(
    rom: Rom,
    world_package: str,
    prsoa_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:
    """
    Most patches are static in size, and are
    meant to be executed before any patches
    changing the size of script files.
    """

    slot_data = orjson.loads(prsoa_patch_instance.get_file("slot_data.json"))
    random_pokemon: bool = bool(slot_data["randomize_pokemon"])

    code_patch(rom, world_package, prsoa_patch_instance, files_dump, slot_data)

    EVENTRECT_PATCHES = defaultdict(list)
    AREA_PATCHES = defaultdict(list)
    FIELD_MAP_PATCHES = defaultdict(list)
    CHAPTER_PATCHES = defaultdict(list)
    QUEST_PATCHES = defaultdict(list)

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
    """A drop in that allows any happiny to be used to help mimi
    A singular happiny will be enough and make happiny leave
    The normal animations where mimi gets her happiny do not play.
    This is one solution to randomize mimi's happiny location,
    but should not stay this way in the future.
    There is a chunk of code that can be replaced to require her
    to get multiple happiny, potentially in place.
    
    This patch means the 3 happiny will not get disabled,
    and stay present and stay even in chapter 27.
    They will stay marked missable and randomized
    for now, but this is something to keep in mind
    
    It's also possible to make you need to capture 3
    happiny at the exact time, that code is currently
    commented out.
    """
    if random_pokemon:
        CHAPTER_PATCHES["c026"] += [
            # PUSH32 17018892		; @5068 -> JMP loc_5203
            (5068, 0x00_59_00_08),
            (5069, 0x0),
            # PUSH 3		; @5206 -> PUSH 0
            (5206, 0x00_00_00_10),
            #
            # # PUSH 0		; @5203 -> PUSH 211
            # (5203, 0x00_D3_00_10),
            # # SYSCALL 2, 131, 1		;syscall_2_131 @5204 -> SYSCALL 2, 141, 1
            # (5204, 0x08_8D_01_01),
            # # PUSH 3		; @5206 -> PUSH 2
            # (5206, 0x00_02_00_10),
        ]

    """mission 3 blastoise"""
    """A patch to allow any blastoise to be usable to complete the 
    forest fire, rather than specifically needing to have 17018880 in your party."""
    # TODO modify this if species field moves become random
    CHAPTER_PATCHES["c026"] += [
        # PUSH32 17018880		; @4429 -> PUSH 5 and NOP 0
        (4429, 0x00_05_00_10),
        (4430, 0x0),
        # SYSCALL 2, 142, 1		;syscall_2_142 @4431 -> SYSCALL 2, 141, 1
        (4431, 0x08_8D_01_01),
    ]

    """mission 4 anti-softlock"""
    """This code is placed in map_patch"""

    """mission 5"""
    """Allows leaving Puel Sea before completing mission 5.
    a simple check is down to check if still in chapter 29, or not.
    This check now always results in not being in chapter 29.
    """
    EVENTRECT_PATCHES["EventRect011011"] += [
        #  PUSH 29		; @10  -> PUSH 0
        (10, 0x00_00_00_10)
    ]

    """post mission 5"""
    """Allows going back before going to the ranger union"""
    EVENTRECT_PATCHES["EventRect014002"] += [
        #  PUSH 30	; @10   -> PUSH 0
        (10, 0x00_00_00_10)
    ]

    """mission 6"""
    """Enables backtracking before completing mission 6"""
    EVENTRECT_PATCHES["EventRect015102"] += [
        #  PUSH 33		; @12
        (12, 0x00_00_00_10)
    ]

    """Prevents a softlock due to using Crush 4 and destroying the boulder, 
    and going to the east without completing mission 6 first
    Changes were the player is thrown by the trampoline plant
    """
    AREA_PATCHES[16] += [
        #  PUSH 256		; @98
        (98, 0x01_10_00_10),
        #  PUSH 30720		; @99
        (99, 0x4F38_00_10),
    ]

    """partner patches"""

    partners = prsoa_patch_instance.files.get("partners.txt")
    if partners:
        partners = orjson.loads(partners)

        starly, pach, munch, *_ = [data.form_id_to_species[i] for i in partners]

        CHAPTER_PATCHES["c013"] += [
            # 	PUSH 396		; @4460
            # 	PUSH 170		; @4461
            (4460, starly.national_id << 16 | 0x10),
            (4461, 311 << 16 | 0x10),
            # 	PUSH 396		; @8463
            # 	PUSH 170		; @8464
            (8463, starly.national_id << 16 | 0x10),
            (8464, 311 << 16 | 0x10),
            # PUSH 170		; @8557
            (8557, 311 << 16 | 0x10),
            # 	PUSH 396		; @10605
            # 	PUSH 170		; @10606
            (10605, starly.national_id << 16 | 0x10),
            (10606, 311 << 16 | 0x10),
            #  PUSH 396
            *list_of_same_patches(
                starly.national_id << 16 | 0x10,
                [
                    4228,
                    4464,
                    8467,
                    8546,
                    9679,
                    9731,
                    10609,
                    11485,
                    12022,
                ],
            ),
            #
            # PUSH 188
            *list_of_same_patches(
                312 << 16 | 0x10,
                [4495, 8486, 8615, 10634],
            ),
            #  PUSH 417
            *list_of_same_patches(
                pach.national_id << 16 | 0x10,
                [
                    4179,
                    4494,
                    4498,
                    8485,
                    8489,
                    8604,
                    9622,
                    9726,
                    10633,
                    10637,
                    11505,
                    12041,
                ],
            ),
            #
            # PUSH 215
            *list_of_same_patches(
                313 << 16 | 0x10,
                [4529, 8508, 8673, 10662],
            ),
            #  PUSH 446
            *list_of_same_patches(
                pach.national_id << 16 | 0x10,
                [
                    4203,
                    4528,
                    4532,
                    8507,
                    8511,
                    8662,
                    9627,
                    9674,
                    10661,
                    10665,
                    11525,
                    12060,
                ],
            ),
        ]

        """untested so far, as this might need other patches"""
        # kricketot = ...
        # CHAPTER_PATCHES["c029"] += [
        #     # PUSH 175		; @3670
        #     (3670, kricketot << 16 | 0x10),  # kricketot
        # ]
        # will need to randomize: m008_006 NPC 12, NPC 8
        # will need to edit a form to be a partner?
        # will need to patch a lot of text

    unlock_partner_as_items = False
    if unlock_partner_as_items:

        """Makes cranidos automatically leave"""
        QUEST_PATCHES["q035"] += [
            # PUSH 1		; @966 -> JMP loc_1177
            (966, 0x00_D2_00_08)
        ]

        # TODO UNTESTED (nobody has time for that)
        QUEST_PATCHES["q045"] += [
            # PUSH 1		; @987 -> JMP loc_1197
            (987, 0x00_D1_00_08)
        ]

    early_staraptor = True
    if early_staraptor:
        m003_st = [
            2,
            3,
            5,
            7,
            9,
            11,
            13,
            15,  # 18,?? not same spot likely
            21,
            23,
            24,
            26,
            27,
            28,
            29,
            30,
            31,
            33,
            # 35, not same
            36,
            38,
            39,
            41,
            43,
        ]
        for chapter in m003_st:
            chapter = f"c{chapter:03}"
            CHAPTER_PATCHES[chapter] += [
                # m003
                # PUSH 43		; @254  -> PUSH 0
                (254, 0x00_00_00_10),
                # m007
                # PUSH 43		; @278  -> PUSH 0
                (278, 0x00_00_00_10),
                # m009
                # PUSH 43		; @350  -> PUSH 0
                (350, 0x00_00_00_10),
                # m014
                # PUSH 43		; @410  -> PUSH 0
                (410, 0x00_00_00_10),
                # m017
                # PUSH 43		; @551  -> PUSH 0
                (551, 0x00_00_00_10),
                # m018
                # PUSH 43		; @563  -> PUSH 0
                (563, 0x00_00_00_10),
            ]

    if random_pokemon:
        ...
        # m010_003 = CompactMapData.from_map_name(prsoa_patch_instance, "m010_003")
        # toxicroak = m010_003.npcs[0]
        # CHAPTER_PATCHES["c028"] += [
        #     # PUSH 221		; @6557
        #     (6557, toxicroak << 16 | 0x10),
        # ]

        # """rampardos event"""
        # This one does not work right now and requires more work
        # m016_004 = CompactMapData.from_map_name(prsoa_patch_instance, "m016_004")
        # # rampardos = m016_004.pokemon[2]
        # rampardos = 230
        # rampardos_browser_id = 159 - 1  # gardevoir
        # CHAPTER_PATCHES["c033"] += [
        #     # # PUSH 409		; @3356 maybe
        #     # (3356, rampardos << 16 | 0x10),
        #     #  PUSH 409	; @3411
        #     (3411, rampardos << 16 | 0x10),
        #     # # PUSH 409		; @3967  maybe
        #     # (3967, rampardos << 16 | 0x10),
        #     ## based on a hunch, unknown what it does, maybe sound or something
        #     #  PUSH 84	; @4464
        #     # (4464, rampardos_browser_id << 16 | 0x10),
        #     # (4630, rampardos_browser_id << 16 | 0x10),
        #     # (4919, rampardos_browser_id << 16 | 0x10),
        #     # (5030, rampardos_browser_id << 16 | 0x10),
        # ]

    for eventrect, writes in EVENTRECT_PATCHES.items():
        base_num = eventrect.strip("EventRect")[0:3]
        file_name = f"/data/Script/field/eventrect/er{base_num}/{eventrect}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)

    for area_num, writes in AREA_PATCHES.items():
        file_name = f"/data/Script/area/m{area_num:03}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)

    for map_name, writes in FIELD_MAP_PATCHES.items():
        area = map_name.split("_")[0]
        file_name = f"/data/Script/field/map/{area}/{map_name}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)

    for chapter, writes in CHAPTER_PATCHES.items():
        file_name = f"/data/Script/chapter/{chapter}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)

    for chapter, writes in QUEST_PATCHES.items():
        file_name = f"/data/Script/quest/{chapter}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)


def code_patch(
    rom: Rom,
    world_package: str,
    prsoa_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
    slot_data,
):
    NOP_INSTRUCTION = 0xE3A00000
    patches = []

    """a patch that prevents partner being set to caught"""
    # This bugs out the tribune quest do to not having one of the three partners unlocked
    # therefore softlocking the game infinitely
    # verify impact / coverage
    # patches.append(
    #     (0x0327D0, NOP_INSTRUCTION),
    # )

    """instant text speed"""
    # just forces it in, which means no custom text speeds are used anymore
    patches += [
        (0xA854, 0xE3A00000),
        (0xA858, 0xE584009C),
        (0xA85C, 0xEA000005),
    ]

    data = bytearray(rom.arm9)

    for offset, instruction in patches:
        struct.pack_into("<I", data, offset, instruction)

    partners = prsoa_patch_instance.files.get("partners.txt")
    if partners:
        partners = orjson.loads(partners)
        offset = 0x02034F9C - 0x02000000
        ARM_INSTRUCTION_BYTES = [
            "0214A0E3",  # 02034F9C: mov   r1, #0x02000000
            "0d1981e3",  # 02034FA0: orr   r1, r1, #0x34000
            "0f1c81e3",  # 02034fa8: orr   r1,r1,#0xf00
            "D81081E3",  # 02034FA4: orr   r1, r1, #0xd8        (r1 = 0x02034FD8)
            "0020A0E3",  # 02034FA8: mov   r2, #0x0
            "B030D1E1",  # 02034FAC: ldrh  r3, [r1, #0]
            "021081E2",  # 02034FB0: add   r1, r1, #0x2
            "030050E1",  # 02034FB4: cmp   r0, r3
            "0100A003",  # 02034FB8: moveq r0, #0x1
            "1EFF2F01",  # 02034FBC: bxeq  lr
            "012082E2",  # 02034FC0: add   r2, r2, #0x1
            "120052E3",  # 02034FC4: cmp   r2, #0x12
            "F7FFFF1A",  # 02034FC8: bne   0x02034FAC
            "0000A0E3",  # 02034FCC: mov   r0, #0x0
            "1EFF2FE1",  # 02034FD0: bx    lr
        ]
        code_bytes = bytes.fromhex("".join(ARM_INSTRUCTION_BYTES))

        partner_ids = list(range(311, 311 + min(len(partners), 18))) + [0] * max(
            0, 18 - len(partners)
        )  # because imagine making this match any length of partners, has to be exactly 18.
        table_bytes = struct.pack(
            "<18H",
            *partner_ids,
        )

        is_partner_patch = code_bytes + table_bytes

        data[offset : offset + len(is_partner_patch)] = is_partner_patch

        # improve patch quality
        # overlay 0, 0213a658
        offset = 0x1DC78
        overlay = bytearray(rom.arm9_overlays[0].data)

        OVERLAY_INSTRUCTION_BYTES = ["5600a0e3", "1eff2fe1"]
        get_value_patch = bytes.fromhex("".join(OVERLAY_INSTRUCTION_BYTES))
        overlay[offset : offset + len(get_value_patch)] = get_value_patch
        rom.arm9_overlays[0].data = bytes(overlay)
        #  patch GetPartnerIndexFromFormId
        #  don't know current impact of this...

    rom.arm9 = bytes(data)
