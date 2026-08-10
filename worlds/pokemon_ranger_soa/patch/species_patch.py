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

    patches: Dict[int, FormPatch] = {}
    world = prsoa_patch_instance.world

    for i, species in world.modified_species.items():
        for j, form_data in species.forms.items():
            patches[j] = FormPatch(j, species.national_id)

    # if world.options.randomize_partners != RandomizePartners.option_vanilla:
    #     a, b, c = world.modified_starters
    #     patches[170].national_id = data.species[a].national_id
    #     patches[188].national_id = data.species[b].national_id
    #     patches[215].national_id = data.species[c].national_id

    opened_zipfile.writestr(
        "species.json",
        orjson.dumps({str(form_id): p.to_dict() for form_id, p in patches.items()}),
    )


def patch(
    rom: Rom,
    world_package: str,
    prsoa_patch_instance: "PokemonRSOAPatch",
    files_dump: dict[str, bytes | bytearray],
) -> None:
    species_file = prsoa_patch_instance.files["species.json"]

    data = orjson.loads(species_file)

    patches: dict[int, FormPatch] = {
        int(form_id): FormPatch.from_dict(patch_data)
        for form_id, patch_data in data.items()
    }

    form_file_name = f"/data/param/PokeID.bin"
    form_file = bytearray(rom.files[form_file_name])
    for i, form_patch in patches.items():
        base_a = 0x28 + form_patch.form_id * 0x1C

        struct.pack_into("<H", form_file, base_a, form_patch.national_id)

    rom.files[form_file_name] = form_file

    from .test_file import test

    rom.files["/data/npc/npc112_LZ.bin"] = test
