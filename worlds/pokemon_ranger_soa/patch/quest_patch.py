import logging
import zipfile
from collections import defaultdict

from ..apnds.rom import Rom

from .base_patch import patch_script_in_place_four_bytes


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

    """quest 35"""
    if randomize_partner_species:
        cranidos = 100
        # will need to randomize: m009_002 NPC 9
        wartortle_with_cranidos = 10
        # randomize m009_002 NPC 10 ???
        QUEST_PATCHES["q035"] += [
            # PUSH 182		; @429
            (429, cranidos << 16 | 0x10),
            # PUSH 4		; @431
            (431, wartortle_with_cranidos << 16 | 0x10),
        ]

    for chapter, writes in QUEST_PATCHES.items():
        file_name = f"/data/Script/quest/{chapter}.fsb"
        patch_script_in_place_four_bytes(rom, file_name, writes)
