import os
from collections.abc import Mapping
from dataclasses import fields
from typing import Any, Dict, List, Set, ClassVar

import settings
from Fill import sweep_from_pool
from Options import Option
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

    ut_can_gen_without_yaml = True  # Needed to inform UT that no yaml is needed

    def __init__(self, multiworld, player):
        super(PokemonRSOA, self).__init__(multiworld, player)

        self.blacklist_captures = set()

        self.exclude_field_moves = set()

        self.seed = 0  # Just an initialization value, it will properly be set in generate_early()

    def get_filler_item_name(self) -> str:
        return "Woah. This is worthless!"

    def generate_early(self) -> None:

        ut_active = False
        # Check whether this is a fake generation performed by UT.
        if hasattr(self.multiworld, "re_gen_passthrough"):
            if self.game in self.multiworld.re_gen_passthrough:
                ut_active = True
                # Retrieve slot data from UT.
                re_gen_slot_data: dict[str, Any] = self.multiworld.re_gen_passthrough[self.game]
                # Populate options from slot data (for yaml-less tracking).
                # This goes through all of your options and replaces their (default due to yaml-less) values
                # with what was stored in slot data.
                for f in fields(PokemonRSOAOptions):
                    opt: Option | None = getattr(self.options, f.name, None)
                    if opt is not None:
                        setattr(self.options, f.name, opt.from_any(re_gen_slot_data[f.name]))
                # Get the seed from slot data.
                self.seed = re_gen_slot_data["seed"]

        if not ut_active:
            # Real generation, so instead generate a seed.
            self.seed = self.random.getrandbits(64)

        # "Restart" this world's RNG using the seed that was either generated in a real world
        # or loaded from slot data (if this a UT re-generation).
        # This will make the fake world generate exactly like how the actual world generated.
        self.random.seed(self.seed)

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

        # self.blacklisted_captures = {
        #     browser_number
        #     for browser_number, species in data.species.items()
        #     if species.name not in possible_species
        # }

        self.blacklisted_captures = set()

    def create_regions(self) -> None:
        regions.create_and_connect_regions(self)
        locations.create_all_locations(self)

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
        slot_data["seed"] = self.seed  # Needs to be sent to UT

        return slot_data

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        # This is a helper function for UT that, when just returning its input, tells UT to start a fake generation
        # using that slot data.
        return slot_data
