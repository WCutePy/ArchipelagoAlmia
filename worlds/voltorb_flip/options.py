import dataclasses

from BaseClasses import PlandoOptions
from Options import PerGameCommonOptions, Choice, OptionCounter, OptionError
from worlds.AutoWorld import World


class Goal(Choice):
    """
    Select your goal.

    - **Levels** - Win all levels you have checks for.
    - **Coins** - Collect enough coins to check all coin locations.
    """
    display_name = "Goal"
    option_levels = 0
    option_coins = 1
    default = 0


class LevelLocationsAdjustments(OptionCounter):
    """
    Adjust various things about the **Win level x** locations.

    - **Maximum** - The maximum level that has a location. Allowed values are in range 1 to 8.
    """
    display_name = "Level Locations Adjustments"
    valid_keys = [
        "Maximum",
    ]
    default = {
        "Maximum": 7,
    }

    def verify(self, world: type[World], player_name: str, plando_options: PlandoOptions) -> None:
        super().verify(world, player_name, plando_options)

        errors = []

        if not 1 <= self.value["Maximum"] <= 8:
            errors.append(f"Maximum: {self.value['Maximum']} not in range 10 to 50000")

        if len(errors) != 0:
            errors = [f"For option {getattr(self, 'display_name', self)} of player {player_name}:"] + errors
            raise OptionError("\n".join(errors))


class CoinLocationsAdjustments(OptionCounter):
    """
    Adjust various things about the **Collect x coins** locations.

    - **Maximum** - The maximum amount of coins that locations have. Allowed values are in range 10 to 50000.
    - **Steps** - The amount of coins needed for each next location. Allowed values are in range 10 to 50000. Cannot be higher than **Maximum**.
    - **Regions** - Evenly distributes all coin locations across that amount of regions. Minimum 2. Cannot be higher than **Maximum** // **Steps**. Only works with experimental logic. Default of -1 ignores this option.
    """
    display_name = "Coin Locations Adjustments"
    valid_keys = [
        "Maximum",
        "Steps",
        "Regions"
    ]
    default = {
        "Maximum": 10000,
        "Steps": 1000,
        "Regions": -1,
    }

    def verify(self, world: type[World], player_name: str, plando_options: PlandoOptions) -> None:
        super().verify(world, player_name, plando_options)

        errors = []

        if not 10 <= self.value["Maximum"] <= 50000:
            errors.append(f"Maximum: {self.value['Maximum']} not in range 10 to 50000")
        if not 10 <= self.value["Steps"] <= 50000:
            errors.append(f"Steps: {self.value['Steps']} not in range 10 to 50000")
        if self.value["Steps"] > self.value["Maximum"]:
            errors.append(f"Steps: {self.value['Steps']} is higher than Maximum: {self.value['Maximum']}")

        if self.value["Regions"] != -1 and not self.value["Regions"] >= 2:
            errors.append(f"Regions: A minimum of 2 region must be set when setting region count")
        if self.value["Regions"] != -1 and self.value["Regions"] > self.value["Maximum"] // self.value["Steps"]:
            errors.append(f"Regions: {self.value["Regions"]} is higher than Maximum // Steps: {self.value["Maximum"]} // {self.value["Steps"]}")

        if len(errors) != 0:
            errors = [f"For option {getattr(self, 'display_name', self)} of player {player_name}:"] + errors
            raise OptionError("\n".join(errors))


class ArtificialLogic(Choice):
    """
    If enabled, progression is logically blocked by having to receive certain amounts of the "Luck" item
    (without actually requiring them).

    If set to **experimental**, random progression items from the multiworld pool will be used for this game's logic instead
    (without actually requiring them as well). However, be aware of frequent generation failures
    """
    display_name = "Artificial Logic"
    option_off = 0
    option_on = 1
    option_experimental = 2
    default = True


@dataclasses.dataclass
class VoltorbFlipOptions(PerGameCommonOptions):
    goal: Goal
    level_locations_adjustments: LevelLocationsAdjustments
    coin_locations_adjustments: CoinLocationsAdjustments
    artificial_logic: ArtificialLogic
