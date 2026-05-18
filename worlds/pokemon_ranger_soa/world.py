import os
from collections.abc import Mapping
from dataclasses import fields
from typing import Any, Dict, List, Set, ClassVar

import settings
from Fill import sweep_from_pool
from worlds.AutoWorld import World
from . import items, locations, regions, rules
from . import options as prsoa_options
from .data import data
from .client import (
    PokemonRangerSOA,
)  # Unused, but required to register with BizHawkClient
from .options import PokemonRSOAOptions
from .rom import PokemonRangerSOAProcedurePatch, write_tokens

PokemonRangerSOA


class PokemonRangerSOASettings(settings.Group):
    class PokemonRangerSOARomFile(settings.UserFilePath):
        description = "Pokemon Ranger - Shadows of Almia USA ROM File"
        copy_to = "Pokemon Ranger - Shadows of Almia (USA).nds"
        md5s = [PokemonRangerSOAProcedurePatch.hash]

    rom_file: PokemonRangerSOARomFile = PokemonRangerSOARomFile(
        PokemonRangerSOARomFile.copy_to
    )


class PokemonRSOA(World):
    game = "PokemonRangerSOA"

    settings_key = "pokemon_ranger_soa_settings"
    settings: ClassVar[PokemonRangerSOASettings]

    options_dataclass = prsoa_options.PokemonRSOAOptions
    options: prsoa_options.PokemonRSOAOptions

    location_name_to_id = locations.create_location_label_to_id_map()
    item_name_to_id = items.create_item_label_to_code_map()

    origin_region_name = "Overworld"

    blacklisted_captures: Set[int]

    exclude_field_moves: Set[str]

    def __init__(self, multiworld, player):
        super(PokemonRSOA, self).__init__(multiworld, player)

        self.blacklisted_captures = set()

        self.exclude_field_moves = set()

    def get_filler_item_name(self) -> str:
        return "Woah. This is worthless!"

    def generate_early(self) -> None:
        possible_species = [
            "Squirtle",
            "Zubat",
            "Pichu",
            "Taillow",
            "Slakoth",
            "Bidoof",
            "Budew",
            "Doduo",
            "Buneary",
            "Shellos",
            "glameow",
        ]
        self.blacklisted_captures = set()

        # self.blacklisted_captures = {
        #     browser_number
        #     for browser_number, species in data.species.items()
        #     if species.name not in possible_species
        # }

        manually_blacklisted = [
            "Shaymin",
            "Palkia",
            "Dialga",
            "Darkrai",
            # "Regigigas",  # not sure about this one
        ]

        self.blacklisted_captures |= {
            b for b, n in data.species.items() if n.name in manually_blacklisted
        }

    def create_regions(self) -> None:
        all_regions = regions.create_and_connect_regions(self)

        locations.create_all_locations(self, all_regions)

        self.multiworld.regions.extend(all_regions.values())

    def create_items(self) -> None:
        items.create_all_items(self)

    def set_rules(self) -> None:
        rules.set_all_rules(self)

    def generate_output(self, output_directory: str) -> None:

        patch = PokemonRangerSOAProcedurePatch(
            player=self.player, player_name=self.player_name
        )
        write_tokens(self, patch)
        out_file_name = self.multiworld.get_out_file_name_base(self.player)
        patch.write(
            os.path.join(output_directory, f"{out_file_name}{patch.patch_file_ending}")
        )

    def create_item(self, name: str) -> items.PokemonRSOAItem:
        return items.create_item_with_correct_classification(self, name)

    def fill_slot_data(self) -> Mapping[str, Any]:
        # slot_data = self.options.as_dict(
        #     "goal",
        #     "mission_clear_target",
        #     "quest_clear_target",
        #     "capture_count_target",
        #     "capture_rank_count_target",
        #     "capture_rank_rank_target",
        #     "death_link",
        #     "death_link_damage",
        #     "level_up_type",
        #     "level_up_count",
        #     "level_up_increment",
        #     "rank_up_type",
        #     "rank_up_count",
        #     "rank_up_increment",
        # )
        slot_data = self.options.as_dict(*[f.name for f in fields(PokemonRSOAOptions)])
        slot_data["blacklisted_captures"] = self.blacklisted_captures

        return slot_data
