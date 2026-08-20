import copy
import os
from collections.abc import Mapping
from dataclasses import fields, dataclass, field
from typing import Any, Dict, List, Set, ClassVar, Tuple

import settings
from BaseClasses import Tutorial, Location, Item, CollectionState, ItemClassification
from Fill import sweep_from_pool
from Options import Option
from worlds.AutoWorld import World, WebWorld
from . import items, locations, regions, rules
from . import options as prsoa_options
from .data import data, MapData, SpeciesData, Party, ItemCategory
from .client import (
    PokemonRangerSOA,
)  # Unused, but required to register with BizHawkClient
from .items import PokemonRSOAItem
from .options import (
    PokemonRSOAOptions,
    OPTION_GROUPS,
    RandomizePokemon,
    RandomizePartners,
)
from .MonSelect import MonSelect
from .randomize import (
    apply_randomized_pokemon,
    early_place_random_restricted,
    early_place_random_partners,
)
from .rom import PokemonRangerSOAProcedurePatch, write_tokens, PokemonRSOAPatch
from Fill import FillError, fill_restrictive

PokemonRangerSOA


class PokemonRangerSOAWebWorld(WebWorld):
    """
    Webhost info for Pokemon Emerald
    """

    theme = "ocean"

    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to playing Pokémon Ranger: Shadows of Almia with Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["WCutePy"],
    )

    tutorials = [setup_en]
    option_groups = OPTION_GROUPS


class PokemonRangerSOASettings(settings.Group):
    class PokemonRangerSOARomFile(settings.UserFilePath):
        description = "Pokemon Ranger - Shadows of Almia USA ROM File"
        copy_to = "Pokemon Ranger - Shadows of Almia (USA).nds"
        md5s = [PokemonRangerSOAProcedurePatch.hash]

    rom_file: PokemonRangerSOARomFile = PokemonRangerSOARomFile(
        PokemonRangerSOARomFile.copy_to
    )


@dataclass
class CaptureGroup:
    locations: list[Location] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)

    def append(self, other: Location | Item) -> None:
        if isinstance(other, Location):
            self.locations.append(other)
        elif isinstance(other, Item):
            self.items.append(other)
        else:
            raise ValueError(f"Expected a Location or Item, got {type(other).__name__}")

    def __len__(self):
        return len(self.locations)


@dataclass
class CaptureGroups:
    missable: CaptureGroup = field(default_factory=CaptureGroup)
    browser: CaptureGroup = field(default_factory=CaptureGroup)
    capture: CaptureGroup = field(default_factory=CaptureGroup)
    capture_ocean: CaptureGroup = field(default_factory=CaptureGroup)

    browser_before_capture: List[Tuple[Location, Location]] = field(
        default_factory=list
    )
    default_ids_used: Set = field(default_factory=set)
    ocean_ids_used: Set = field(default_factory=set)

    def __len__(self):
        return (
            len(self.missable)
            + len(self.browser)
            + len(self.capture)
            + len(self.capture_ocean)
            + len(self.browser_before_capture)
        )

    def append_capture(self, other: Location | Item, party: Party):
        if party == party.DEFAULT:
            self.capture.append(other)
        elif party == party.OCEAN:
            self.capture_ocean.append(other)

    @property
    def get_ids_all(self) -> List[int]:
        return sorted({*self.default_ids_used, *self.ocean_ids_used})

    @property
    def get_ids_default(self) -> List[int]:
        return sorted(self.default_ids_used)

    @property
    def get_ids_ocean(self) -> List[int]:
        return sorted(self.ocean_ids_used)


class PokemonRSOA(World):
    game = "PokemonRangerSOA"
    web = PokemonRangerSOAWebWorld()

    settings_key = "pokemon_ranger_soa_settings"
    settings: ClassVar[PokemonRangerSOASettings]

    options_dataclass = prsoa_options.PokemonRSOAOptions
    options: prsoa_options.PokemonRSOAOptions

    location_name_to_id = locations.create_location_label_to_id_map()
    item_name_to_id = items.create_item_label_to_code_map()

    origin_region_name = "Overworld"

    blacklisted_captures: Set[int]

    capture_groups: CaptureGroups
    included_browser_entries: Set[int]

    exclude_field_moves: Set[str]

    modified_regions: Dict[str, MapData]
    modified_species: Dict[int, SpeciesData]  # browser id - SpeciesData
    modified_partners: List[int]  # browser id

    ut_can_gen_without_yaml = True  # Needed to inform UT that no yaml is needed
    # topology_present = True

    def __init__(self, multiworld, player):
        super(PokemonRSOA, self).__init__(multiworld, player)

        self.blacklisted_captures = set()
        self.included_browser_entries = set()

        self.capture_groups = CaptureGroups()

        self.exclude_field_moves = set()

        self.seed = 0  # Just an initialization value, it will properly be set in generate_early()

    def get_filler_item_name(self) -> str:
        return "Woah. This is worthless!"

    def generate_early(self) -> None:
        self.options.verify()

        MonSelect.world = self
        self.modified_regions = copy.deepcopy(data.regions)
        for map_name, map_indexes in MonSelect.missable().include.items():
            for i in map_indexes:
                self.modified_regions[map_name].POKEMON_SPAWN[i].missable = True
        for map_name, map_indexes in MonSelect.randomize_false().include.items():
            for i in map_indexes:
                self.modified_regions[map_name].POKEMON_SPAWN[i].randomize = False
        for map_name, map_indexes in MonSelect.browser_before_capture().include.items():
            for i in map_indexes:
                self.modified_regions[map_name].POKEMON_SPAWN[
                    i
                ].browser_before_capture = True
        self.modified_species = copy.deepcopy(data.species)

        ut_active = False
        # Check whether this is a fake generation performed by UT.
        if hasattr(self.multiworld, "re_gen_passthrough"):
            if self.game in self.multiworld.re_gen_passthrough:
                ut_active = True
                # Retrieve slot data from UT.
                re_gen_slot_data: dict[str, Any] = self.multiworld.re_gen_passthrough[
                    self.game
                ]
                # Populate options from slot data (for yaml-less tracking).
                # This goes through all of your options and replaces their (default due to yaml-less) values
                # with what was stored in slot data.
                for f in fields(PokemonRSOAOptions):
                    opt: Option | None = getattr(self.options, f.name, None)
                    if opt is not None:
                        setattr(
                            self.options, f.name, opt.from_any(re_gen_slot_data[f.name])
                        )
                # Get the seed from slot data.
                self.seed = re_gen_slot_data["seed"]

        if not ut_active:
            # Real generation, so instead generate a seed.
            self.seed = self.random.getrandbits(64)

        # "Restart" this world's RNG using the seed that was either generated in a real world
        # or loaded from slot data (if this a UT re-generation).
        # This will make the fake world generate exactly like how the actual world generated.
        self.random.seed(self.seed)

        self.blacklisted_captures = {
            238,  # wailord
            # until I ensure their required field moves are in the pool
            114,  # oddish
            115,  # Gloom
            116,  # Vileplume
            41,  # geodude
            42,  # graveler
            31,  # sudowoodo
            240,  # cacturne
            54,  # torterra
            248,  # bronzor
            30,  # bonsly
            136,  # carnivine
            212,  # abomasnow
            # partners
            26,  # pach
            27,  # munchlax
            23,  # starly
            168,  # chimchar
            206,  # piplup
            52,  # turtwig
            213,  # snorunt
            161,  # machop
            80,  # croagunk
            246,  # hippopotas
            164,  # mime jr.
            82,  # kricketot
            84,  # cranidos
            220,  # misdreavus
            251,  # gible
            244,  # sneasel
            181,  # shieldon
        }

        # self.blacklisted_captures = {
        #     browser_number
        #     for browser_number, species in data.species.items()
        #     if species.name not in possible_species
        # }

        if self.options.randomize_partners != RandomizePartners.option_vanilla:
            early_place_random_partners(self)

        if self.options.randomize_pokemon != RandomizePokemon.option_vanilla:
            early_place_random_restricted(self)

    def create_regions(self) -> None:
        all_regions = regions.create_and_connect_regions(self)

        locations.create_all_locations(self, all_regions)

        self.multiworld.regions.extend(all_regions.values())

    def create_items(self) -> None:
        items.create_all_items(self)

    def set_rules(self) -> None:
        rules.set_all_rules(self)

        if self.options.randomize_pokemon != RandomizePokemon.option_vanilla:
            apply_randomized_pokemon(self)

            import json

            dump = {}

            for region_id, map_data in self.modified_regions.items():
                dump[region_id] = {
                    "map_id": map_data.map_id,
                    "human_name": map_data.HUMAN_NAME,
                    "modified": map_data.modified,
                    "pokemon_spawn": {
                        spawn_id: {
                            "SPECIES_ID": spawn.SPECIES_ID,
                            "SPECIES_NAME": spawn.SPECIES_NAME,
                            "SPAWN_FLAG": spawn.SPAWN_FLAG,
                            "missable": spawn.missable,
                            "one_time": spawn.one_time,
                            "randomize": spawn.randomize,
                            "rules": spawn.rules,
                        }
                        for spawn_id, spawn in map_data.POKEMON_SPAWN.items()
                    },
                }

            with open("mapdata_modified_dump.json", "w", encoding="utf-8") as f:
                json.dump(dump, f, indent=2)

            self.multiworld.state.prog_items[self.player]["power_level"] = 99999

            # for map_name in ["m001_002", "m001_011", "m002_001", "m003_001"]:
            #
            #     map_data: MapData = self.modified_regions[map_name]
            #     for key, values in map_data.POKEMON_SPAWN.items():
            #         if key == 5 and map_name == "m001_011":
            #             continue
            #         map_data.POKEMON_SPAWN[key].SPECIES_ID = 0xAD

    def pre_fill(self) -> None:
        ...
        # self.multiworld.state.prog_items[self.player]["power_level"] = 999999

    def write_spoiler(self, spoiler_handle) -> None:
        browser_instances = sum(
            1
            for loc in self.multiworld.get_locations(self.player)
            if loc.item and loc.item.name.startswith("EVENT_ADD_TO_BROWSER")
        )

        capture_instances = sum(
            1
            for loc in self.multiworld.get_locations(self.player)
            if loc.item and loc.item.name.startswith("EVENT_CAN_CAPTURE")
        )

        spoiler_handle.write("\nPokemon Statistics:\n")
        spoiler_handle.write(
            f"  Unique Browser Captures: {len(self.capture_groups.get_ids_all)}"
        )
        spoiler_handle.write(f"  Browser Instances: {browser_instances}\n")
        spoiler_handle.write(f"  Capture Instances: {capture_instances}\n")

    def generate_output(self, output_directory: str) -> None:

        # patch = PokemonRangerSOAProcedurePatch(
        #     player=self.player, player_name=self.player_name
        # )
        # write_tokens(self, patch)
        # out_file_name = self.multiworld.get_out_file_name_base(self.player)
        # patch.write(
        #     os.path.join(
        #         output_directory, f"{out_file_name}_old{patch.patch_file_ending}"
        #     )
        # )

        PokemonRSOAPatch(
            path=os.path.join(
                output_directory,
                self.multiworld.get_out_file_name_base(self.player)
                + PokemonRSOAPatch.patch_file_ending,
            ),
            world=self,
            player=self.player,
            player_name=self.player_name,
        ).write()

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
            "level_up_type",
            "level_up_count",
            "level_up_increment",
            "rank_up_type",
            "rank_up_count",
            "rank_up_increment",
            "randomize_pokemon",
            "randomize_target_field_move",
        )
        # slot_data = self.options.as_dict(*[f.name for f in fields(PokemonRSOAOptions)])
        slot_data["blacklisted_captures"] = self.blacklisted_captures
        slot_data["seed"] = self.seed  # Needs to be sent to UT

        return slot_data

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        # This is a helper function for UT that, when just returning its input, tells UT to start a fake generation
        # using that slot data.
        return slot_data

    mission_affinities = {
        -1: 150,
        0: 250,
        1: 600,
        2: 900,
        3: 1500,
        4: 1500,
        5: 3200,
        6: 1000000,
        100: 1000000,
    }

    def collect(self, state: CollectionState, item: PokemonRSOAItem) -> bool:
        change = super().collect(state, item)
        if change:
            if ItemCategory.POWER_LEVEL in item.tags:
                state.prog_items[self.player]["power_level"] += 1
            if "fill_restrictive" in state.prog_items[self.player]:
                if "COMPLETE_MISSION" in item.name:
                    mission = int(item.name.strip("COMPLETE_MISSION"))
                    if mission == self.options.mission_clear_target.value:
                        mission = 100
                    state.prog_items[self.player]["power_level"] = (
                        self.mission_affinities[mission]
                    )
            else:
                state.prog_items[self.player]["power_level"] = self.mission_affinities[
                    100
                ]

        return change

    def remove(self, state: CollectionState, item: PokemonRSOAItem) -> bool:
        change = super().remove(state, item)
        if change:
            if ItemCategory.POWER_LEVEL in item.tags:
                state.prog_items[self.player]["power_level"] -= 1
            if "fill_restrictive" in state.prog_items[self.player]:
                if "COMPLETE_MISSION" in item.name:
                    mission = int(item.name.strip("COMPLETE_MISSION")) - 1
                    state.prog_items[self.player]["power_level"] = (
                        self.mission_affinities[mission]
                    )
        return change
