import dataclasses
import logging
import struct
import zipfile
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from dataclasses import dataclass

from orjson import orjson

import NetUtils
from ..apnds.rom import Rom
from ..data import data
from ..options import RandomizePartners

if TYPE_CHECKING:
    from ..rom import PokemonRSOAPatch


@dataclass
class FormPatch:
    form_id: int
    national_id: int

    def to_dict(self) -> dict[str, int]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormPatch":
        return cls(
            form_id=data["form_id"],
            national_id=data["national_id"],
        )


def pokemon_to_npc_sprite(rom: Rom, national_dex: int, npc_form: int) -> None: ...


def write_patch(
    prsoa_patch_instance: "PokemonRSOAPatch", opened_zipfile: zipfile.ZipFile
) -> None:

    # patches: Dict[int, FormPatch] = {}
    world = prsoa_patch_instance.world
    #
    # for i, species in world.modified_species.items():
    #     for j, form_data in species.forms.items():
    #         patches[j] = FormPatch(j, species.national_id)

    if world.modified_partners:
        opened_zipfile.writestr(
            "partners.txt",
            orjson.dumps(world.modified_partners),
        )

    # opened_zipfile.writestr(
    #     "species.json",
    #     orjson.dumps({str(form_id): p.to_dict() for form_id, p in patches.items()}),
    # )


def get_pokeid(form_id: int):
    return 0x28 + form_id * 0x1C


def get_fielddata_pok(form_id: int):
    return 0x24 + form_id * 0x40


def clone_form_to_form_id(
    rom: Rom, form_file: bytearray, from_form: int, to_form: int, zero_field_move=True
):
    base_to = get_pokeid(to_form)

    start = 0x0
    from_data = form_file[get_pokeid(from_form) + start : get_pokeid(from_form) + 0x29]
    if zero_field_move:
        from_data[5] = 0
        from_data[6] = 0
    struct.pack_into(f"<{len(from_data)}B", form_file, base_to + start, *from_data)

    rom.files[f"/data/Script/battle/pokemon/p{to_form:03}.fsb"] = rom.files[
        f"/data/Script/battle/pokemon/p{from_form:03}.fsb"
    ]

    field_data = bytearray(rom.files["/data/field/fielddata.bin"])

    field_data[get_fielddata_pok(to_form) : get_fielddata_pok(to_form) + 0x41] = (
        field_data[get_fielddata_pok(from_form) : get_fielddata_pok(from_form) + 0x41]
    )
    rom.files["/data/field/fielddata.bin"] = bytes(field_data)

    """
    There are more files that need patching to be a full clone, but this is good enough for now!!!
    """


def patch(
    rom: Rom,
    world_package: str,
    prsoa_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:

    # species_file = prsoa_patch_instance.files["species.json"]
    # data = orjson.loads(species_file)
    #
    # patches: dict[int, FormPatch] = {
    #     int(form_id): FormPatch.from_dict(patch_data)
    #     for form_id, patch_data in data.items()
    # }

    form_file_name = f"/data/param/PokeID.bin"
    form_file = bytearray(rom.files[form_file_name])

    # for i, form_patch in patches.items():
    #     base_a = 0x28 + form_patch.form_id * 0x1C
    #
    #     struct.pack_into("<H", form_file, base_a, form_patch.national_id)

    partners = prsoa_patch_instance.files.get("partners.txt")
    if partners:
        partners = orjson.loads(partners)
        print(type(partners), partners)
        for i in range(0, len(partners)):
            pokemon = data.species[partners[i]]
            from_form_id = list(pokemon.forms.keys())[0]
            clone_form_to_form_id(rom, form_file, from_form_id, 311 + i)

    rom.files[form_file_name] = bytes(form_file)

    from .test_file import test

    rom.files["/data/npc/npc112_LZ.bin"] = test
