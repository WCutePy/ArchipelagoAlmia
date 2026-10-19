import logging
import zipfile
from collections import defaultdict
from ..apnds.rom import Rom

from .base_patch import patch_script_in_place_four_bytes
from .map_patch import CompactMapData


def write_patch(
    prsoa_patch_instance: "PokemonRSOAPatch", opened_zipfile: zipfile.ZipFile
) -> None: ...


def patch(
    rom: Rom,
    world_package: str,
    prsoa_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:
    logging.warning(f"patching in quests")

    QUEST_PATCHES = defaultdict(list)
    randomize_partner_species = True
    randomize_partner_species = False
    #
    # """quest 3"""
    # mon = ...
    # quest_3_push_combee = ...
    # QUEST_PATCHES["q003"] += [
    #     # PUSH 186		; @167 -> PUSH X
    #     (167, quest_3_push_combee)
    #     # PUSH 186		; @173 -> PUSH X
    #     (173, quest_3_push_combee)
    # ]
    # # TODO change messages to replace combee for mon.name

    # """quest 12"""
    # mon = ...
    # quest_12_push_cherrim = mon << 16 | 0x10
    # QUEST_PATCHES["Q012"] += [
    #     # PUSH 192		; @116
    #     (116, quest_12_push_cherrim),
    #     # 	PUSH 192		; @122
    #     (122, quest_12_push_cherrim),
    # ]

    # """quest 35"""
    # wartortle_with_cranidos = 4
    # # randomize m009_002 NPC 10 ???
    # QUEST_PATCHES["q035"] += [
    # # PUSH 4		; @431
    # (431, wartortle_with_cranidos << 16 | 0x10),
    # ]

    # # """quest 16"""
    # # somehow seems to not be functional code!!!
    # m021_001 = CompactMapData.from_map_name(prsoa_patch_instance, "m021_001")
    # vespiqueen = m021_001.pokemon[6]
    # combee = m021_001.pokemon[14]
    # QUEST_PATCHES["q016"] += [
    #     # PUSH 187		; @516
    #     (516, vespiqueen << 16 | 0x10),
    #     # PUSH 186		; @518
    #     (518, combee << 16 | 0x10),
    #     # PUSH 186		; @520
    #     (520, combee << 16 | 0x10),
    #     # PUSH 187		; @918
    #     (918, vespiqueen >> 16 | 0x10),
    #     # PUSH 186		; @920
    #     (920, combee << 16 | 0x10),
    #     # PUSH 186		; @922
    #     (922, combee << 16 | 0x10),
    # ]

    for chapter, writes in QUEST_PATCHES.items():
        file_name = f"/data/Script/quest/{chapter}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)
