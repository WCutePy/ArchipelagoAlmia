import dataclasses
import logging
import struct
import zipfile
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from dataclasses import dataclass

from ..apnds.rom import Rom
from ..apnds.narc import Narc
from ..apnds.lz import compress, decompress
from ..options import RandomizePokemonEncounters

if TYPE_CHECKING:
    from ..rom import PokemonRSOAPatch


def write_patch(
    prsoa_patch_instance: "PokemonRSOAPatch", opened_zipfile: zipfile.ZipFile
) -> None:

    for map_name, map_data in prsoa_patch_instance.world.modified_regions.items():
        if not map_data.modified:
            continue
        objects = []

        npc = []

        pokemon = []
        if (
            prsoa_patch_instance.world.options.randomize_pokemon
            != RandomizePokemonEncounters.option_vanilla
        ):
            for i, object_data in map_data.TARGETS.items():
                objects.append(object_data.TARGET_ID)

            for i, npc_data in map_data.NPCS.items():
                npc.append(npc_data.unk2)

            for i, spawn_data in map_data.POKEMON_SPAWN.items():
                pokemon.append(spawn_data.SPECIES_ID)

        data = (
            struct.pack("<III", len(objects), len(npc), len(pokemon))
            + struct.pack(f"<{len(objects)}H", *objects)
            + struct.pack(f"<{len(npc)}H", *npc)
            + struct.pack(f"<{len(pokemon)}H", *pokemon)
        )
        opened_zipfile.writestr(f"map/{map_name}.bin", data)


def patch_map(rom: Rom, map_name: str, data: Dict[int, Any]) -> None:
    if not data:
        return

    file_name = f"/data/field/map/{map_name}.map.dat.lz"

    narc_map_b = rom.files[file_name]
    narc_map_b_uc = decompress(narc_map_b)
    narc_map = Narc.from_bytes(narc_map_b_uc)

    lyr_index = None
    for i, map_bin in enumerate(narc_map.files):
        if map_bin[:4] == b"LYR\x00":
            lyr_index = i

    lyr_b = narc_map.files[lyr_index]
    lyr_header, narc_lyr_b = lyr_b[:4], lyr_b[4:]
    narc_lyr = Narc.from_bytes(narc_lyr_b)

    objects = data.get(0x04, [])
    triggers = data.get(0x07, {})
    npc = data.get(0x08, [])
    pokemon = data.get(0x09, [])

    layer_type_index = defaultdict(int)

    logging.warning(
        f"Writing pokemon: {data.get(0x09, [])=}, {data.get(0x08, [])=}, {data.get(0x04, [])=}"
    )

    for i, file_group in enumerate(narc_lyr.files):
        narc_layer_list = Narc.from_bytes(file_group)

        for j, layer_data in enumerate(narc_layer_list.files):
            layer_type = struct.unpack("<I", layer_data[:4])[0]
            layer_data = bytearray(layer_data)

            if objects and layer_type == 0x04:
                offset = 8  # ? not sure if that's the right one
                entry_count = (len(layer_data) - 8) // 12
                for _ in range(entry_count):
                    struct.pack_into(
                        "<H", layer_data, offset + 6, objects[layer_type_index[4]]
                    )
                    offset += 12
                    layer_type_index[4] += 1
            if triggers and layer_type == 0x07:
                offset = 8
                entry_count = (len(layer_data) - 8) // 11
                for _ in range(entry_count):
                    index = layer_type_index[7]
                    layer_type_index[7] += 1
                    if index not in triggers:
                        offset += 10
                        continue
                    entry = triggers.get(index, {})
                    logging.warning(f"{map_name}, trigger {index}", entry)

                    if "x" in entry:
                        struct.pack_into("<H", layer_data, offset, entry["x"])
                    offset += 2
                    if "y" in entry:
                        struct.pack_into("<H", layer_data, offset, entry["y"])
                    offset += 2
                    if "width" in entry:
                        struct.pack_into("<H", layer_data, offset, entry["width"])
                    offset += 2
                    if "height" in entry:
                        struct.pack_into("<H", layer_data, offset, entry["height"])
                    offset += 4

            elif npc and layer_type == 0x08:
                offset = 8 + 6  # ? not sure if that's the right one
                entry_count = (len(layer_data) - 8) // 11
                for _ in range(entry_count):
                    struct.pack_into("<H", layer_data, offset, npc[layer_type_index[8]])
                    offset += 11
                    layer_type_index[8] += 1
            elif pokemon and layer_type == 0x09:
                entry_count = (len(layer_data) - 8) // 10
                offset = 8 + 6
                for _ in range(entry_count):
                    struct.pack_into(
                        "<H", layer_data, offset, pokemon[layer_type_index[9]]
                    )
                    offset += 10

                    layer_type_index[9] += 1
            narc_layer_list.files[j] = layer_data
        narc_lyr.files[i] = narc_layer_list.to_bytes()

    narc_map.files[lyr_index] = lyr_header + narc_lyr.to_bytes()

    narc_map_rec = narc_map.to_bytes()
    narc_map_rec_b = compress(narc_map_rec)
    rom.files[file_name] = narc_map_rec_b

    logging.warning(f"Map has been edited: {narc_map_b != narc_map_rec_b}")
    logging.warning(f"Patched map: {map_name}")


def add_map_base_patches(map_name: str, data: Dict[int, Any]) -> None:
    """Mission 4, anti softlock if you enter the west of
    pueltown through the east of pueltown clearing the center gigaremo
    It would be better to patch the wall in m010_022 in the first place,
    however that would require complex script changes.
    """
    if map_name == "m010_001":
        data[0x07] = {
            2: {
                "y": 250,
                "height": 64,
            }
        }


@dataclass
class CompactMapData:
    objects: List[int]
    npcs: List[int]
    pokemon: List[int]

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional["CompactMapData"]:
        (
            num_objects,
            num_npc,
            num_pokemon,
        ) = struct.unpack_from("<III", data, 0)
        if num_objects + num_npc + num_pokemon == 0:
            return None
        offset = 12
        objects = list(struct.unpack_from(f"<{num_objects}H", data, offset))
        offset += num_objects * 2

        npcs = list(struct.unpack_from(f"<{num_npc}H", data, offset))
        offset += num_npc * 2

        pokemon = list(struct.unpack_from(f"<{num_pokemon}H", data, offset))

        return CompactMapData(objects, npcs, pokemon)

    @classmethod
    def from_map_name(
        cls, prsoa_patch_instance: "PokemonRSOAPatch", map_name: str
    ) -> "CompactMapData":
        file_name = f"map/{map_name}.bin"
        patch_file = prsoa_patch_instance.get_file(file_name)
        return cls.from_bytes(patch_file)


def patch(
    rom: Rom,
    world_package: str,
    prsoa_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:

    for file_name, file_data in prsoa_patch_instance.files.items():
        if not file_name.startswith("map/m"):
            continue
        patch_file = prsoa_patch_instance.get_file(file_name)
        map_name = file_name[4:-4]

        # if map_name != "m005_003" and map_name != "m003_001":
        #     continue

        map_data = CompactMapData.from_bytes(patch_file)

        data = {0x04: map_data.objects, 0x08: map_data.npcs, 0x09: map_data.pokemon}
        add_map_base_patches(map_name, data)

        patch_map(rom, map_name, data)
