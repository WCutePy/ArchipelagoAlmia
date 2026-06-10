import logging
import struct
import zipfile
from typing import TYPE_CHECKING

from ..apnds.rom import Rom
from ..apnds.narc import Narc
from ..apnds.lz import compress, decompress
from ..options import RandomizePokemon

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
            != RandomizePokemon.option_vanilla
        ):
            for i, spawn_data in map_data.POKEMON_SPAWN.items():
                pokemon.append(spawn_data.SPECIES_ID)

            for i, npc_data in map_data.NPC.items():
                npc.append(npc_data.unk2)
        data = (
            struct.pack("<III", len(objects), len(npc), len(pokemon))
            + struct.pack(f"<{len(objects)}H", *objects)
            + struct.pack(f"<{len(npc)}H", *npc)
            + struct.pack(f"<{len(pokemon)}H", *pokemon)
        )
        opened_zipfile.writestr(f"map/{map_name}.bin", data)


def patch_map(
    rom: Rom, map_name: str, objects: list[int], npc: list[int], pokemon: list[int]
) -> None:
    if not objects and not pokemon and not npc:
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

    objects_index = 0
    npc_index = 0
    pokemon_index = 0

    logging.warning(f"Writing pokemon: {pokemon=}, {npc=}, {objects}")

    for i, file_group in enumerate(narc_lyr.files):
        narc_layer_list = Narc.from_bytes(file_group)

        for j, layer_data in enumerate(narc_layer_list.files):
            layer_type = struct.unpack("<I", layer_data[:4])[0]

            if objects and layer_type == 0x04:
                ...
            elif npc and layer_type == 0x08:
                layer_data = bytearray(layer_data)

                offset = 0
                entry_count = (len(layer_data) - 8) // 11
                for _ in range(entry_count):
                    struct.pack_into("<H", layer_data, offset, npc[npc_index])
                    offset += 1
                    npc_index += 1
            elif pokemon and layer_type == 0x09:
                logging.warning(f"Pokemon layer: {j}")

                layer_data = bytearray(layer_data)
                offset = 0
                entry_count = (len(layer_data) - 8) // 10
                offset += 8 + 6
                for _ in range(entry_count):
                    struct.pack_into("<H", layer_data, offset, pokemon[pokemon_index])
                    offset += 10

                    pokemon_index += 1
                narc_layer_list.files[j] = layer_data
        narc_lyr.files[i] = narc_layer_list.to_bytes()

    narc_map.files[lyr_index] = lyr_header + narc_lyr.to_bytes()

    narc_map_rec = narc_map.to_bytes()
    narc_map_rec_b = compress(narc_map_rec)
    rom.files[file_name] = narc_map_rec_b

    logging.warning(f"Map has been edited: {narc_map_b != narc_map_rec_b}")
    logging.warning(f"Patched map: {map_name}")


def patch_scripts(
    rom: Rom,
): ...


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

        (
            num_objects,
            num_npc,
            num_pokemon,
        ) = struct.unpack_from("<III", patch_file, 0)
        offset = 12
        objects = list(struct.unpack_from(f"<{num_objects}H", patch_file, offset))
        offset += num_objects * 2

        npc = list(struct.unpack_from(f"<{num_npc}H", patch_file, offset))
        offset += num_npc * 2

        pokemon = list(struct.unpack_from(f"<{num_pokemon}H", patch_file, offset))

        patch_map(rom, map_name, objects, npc, pokemon)
