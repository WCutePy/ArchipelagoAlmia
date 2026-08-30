import os
from dataclasses import fields
from typing import ClassVar, Any, Mapping

import settings
from BaseClasses import Tutorial
from Options import Option
from worlds.AutoWorld import WebWorld, World

from .options import PokemonTrozeiOptions, OPTION_GROUPS
from . import regions, items, rules, rom
from .client import (
    PokemonTrozeiCient,
)  # Unused, but required to register with BizHawkClient


class PokemonTrozeiWebWorld(WebWorld):
    """
    Webhost info for Pokemon Emerald
    """

    theme = "ocean"

    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to playing Pokémon Trozei.",
        "English",
        "setup_en.md",
        "setup/en",
        ["WCutePy"],
    )

    tutorials = [setup_en]
    option_groups = OPTION_GROUPS


class PokemonTrozeiSettings(settings.Group):
    class PokemonLinkRomFile(settings.UserFilePath):
        description = "Pokemon Link ROM File"
        copy_to = "Pokemon Link.nds"
        md5s = ["5af68afc469ee54adc3721d9d8913904"]

    link_rom_file: PokemonLinkRomFile = PokemonLinkRomFile(PokemonLinkRomFile.copy_to)


class PokemonTrozei(World):
    game = "Pokemon Trozei"
    web = PokemonTrozeiWebWorld()

    settings_key = "pokemon_trozei_settings"
    settings: ClassVar[PokemonTrozeiSettings]

    options_dataclass = PokemonTrozeiOptions
    options: PokemonTrozeiOptions

    location_name_to_id = regions.create_location_label_to_id_map()
    item_name_to_id = items.create_item_label_to_code_map()

    origin_region_name = "Menu"

    ut_can_gen_without_yaml = True

    def __init__(self, multiworld, player):
        super(PokemonTrozei, self).__init__(multiworld, player)

        self.seed = 0  # Just an initialization value, it will properly be set in generate_early()

    def create_item(self, name: str) -> items.PokemonTrozeiItem:
        return items.create_item_with_correct_classification(self, name)

    def get_filler_item_name(self) -> str:
        options = [
            "Coin x1",
            "Coin x3",
            "Coin x5",
        ]
        value, *_ = self.random.choices(options, weights=[0.6, 0.3, 0.1], k=1)
        return value

    def generate_early(self) -> None:

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
                for f in fields(PokemonTrozeiOptions):
                    opt: Option | None = getattr(self.options, f.name, None)
                    if opt is not None and f.name in re_gen_slot_data:
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

    def create_regions(self) -> None:
        all_regions = regions.create_and_connect_regions(self)

        self.multiworld.regions.extend(all_regions.values())

    def create_items(self) -> None:
        items.create_all_items(self)

    def set_rules(self) -> None:
        rules.set_all_rules(self)

    def generate_output(self, output_directory: str) -> None:
        patch = rom.PokemonLinkProcedurePatch(
            player=self.player, player_name=self.player_name
        )

        rom.write_tokens(self, patch)

        out_file_name = self.multiworld.get_out_file_name_base(self.player)
        patch.write(
            os.path.join(output_directory, f"{out_file_name}{patch.patch_file_ending}")
        )

    def fill_slot_data(self) -> Mapping[str, Any]:
        slot_data = self.options.as_dict(
            "required_bosses",
            "hard_mode",
            "hard_trap_count",
            "death_link",
        )

        slot_data["seed"] = self.seed
        return slot_data

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        # This is a helper function for UT that, when just returning its input, tells UT to start a fake generation
        # using that slot data.
        return slot_data
