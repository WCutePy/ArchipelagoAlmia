from collections.abc import Mapping
from typing import Any, Dict, List, Set

from Fill import sweep_from_pool
from worlds.AutoWorld import World
from . import items, locations, regions, rules
from . import options as prsoa_options
from .data import data
from .client import (
    PokemonRangerSOA,
)  # Unused, but required to register with BizHawkClient

PokemonRangerSOA


class PokemonRSOA(World):
    game = "PokemonRangerSOA"

    options_dataclass = prsoa_options.PokemonRSOAOptions
    options: prsoa_options.PokemonRSOAOptions

    location_name_to_id = locations.create_location_label_to_id_map()
    item_name_to_id = items.create_item_label_to_code_map()

    origin_region_name = "Overworld"

    blacklisted_captures: Set[int]

    def __init__(self, multiworld, player):
        super(PokemonRSOA, self).__init__(multiworld, player)

        self.blacklist_captures = set()

    def get_filler_item_name(self) -> str:
        return "Filler Item"

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

        # self.blacklisted_captures = {
        #     browser_number
        #     for browser_number, species in data.species.items()
        #     if species.name not in possible_species
        # }

        self.blacklisted_captures = set()

    def create_regions(self) -> None:
        regions.create_and_connect_regions(self)
        locations.create_all_locations(self)

    def set_rules(self) -> None:
        rules.set_all_rules(self)

    def create_items(self) -> None:
        items.create_all_items(self)

    def create_item(self, name: str) -> items.PokemonRSOAItem:
        return items.create_item_with_correct_classification(self, name)

    def fill_slot_data(self) -> Mapping[str, Any]:
        slot_data = self.options.as_dict(
            "goal",
            "mission_clear_target",
            "quest_clear_target",
            "capture_count_target",
            "capture_rank_count_target",
            "capture_rank_rank_target",
            "death_link",
            "death_link_damage",
        )
        slot_data["blacklisted_captures"] = self.blacklisted_captures

        print(slot_data)

        return slot_data
