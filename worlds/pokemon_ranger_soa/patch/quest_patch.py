import zipfile
from collections import defaultdict

from ..apnds.rom import Rom

from .base_patch import patch_script_in_place_singular_byte


def write_patch(
    prsoa_patch_instance: "PokemonRSOAPatch", opened_zipfile: zipfile.ZipFile
) -> None:
    ...


def patch_map(
    rom: Rom, map_name: str, objects: list[int], npc: list[int], pokemon: list[int]
) -> None:


    QUEST_PATCHES = defaultdict(list)

    """quest 3"""
    mon = ...
    quest_3_push_combee = ...
    QUEST_PATCHES["q003"] += [
        # PUSH 186		; @167 -> PUSH X
        (167 * 4, quest_3_push_combee)
        # PUSH 186		; @173 -> PUSH X
        (173 * 4, quest_3_push_combee)
    ]
    # TODO change messages to replace combee for mon.name