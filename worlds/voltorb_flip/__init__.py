import logging
from typing import ClassVar, Mapping, Any

import settings
from BaseClasses import Item, ItemClassification, Region, MultiWorld
from worlds.AutoWorld import World
from . import client, options, locations


client.register_client()


def create_coin_region_name(value, max_regions=None):
    if isinstance(value, int):
        return f"Coin region-{value}"
    else:
        raise NotImplementedError


class VoltorbFlipSettings(settings.Group):

    class AllowExperimentalLogic(settings.Bool):
        """Allows the **experimental** choice in the **Artificial Logic** option."""

    allow_experimental_logic: AllowExperimentalLogic | bool = False


class VoltorbFlipWorld(World):
    game = "Voltorb Flip"
    options_dataclass = options.VoltorbFlipOptions
    options: options.VoltorbFlipOptions
    settings_key = "voltorb_flip_settings"
    settings: ClassVar[VoltorbFlipSettings]
    topology_present = True
    item_name_to_id = {"Luck": 50000}
    location_name_to_id = locations.locations
    progression_list: ClassVar[list[tuple[str, int]]] = []  # Only used in set_rules, so reusable for other slots

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)
        self.regions: dict[str, Region] = {}
        self.max_level = 0
        self.last_coin = 0
        self.luck_classification = ItemClassification.progression_deprioritized_skip_balancing

    def create_item(self, name: str) -> "Item":
        return VoltorbFlipItem(name, self.luck_classification, self.item_name_to_id[name], self.player)

    def get_filler_item_name(self) -> str:
        return "Luck"

    def create_regions(self) -> None:
        self.regions = {
            "Menu": Region("Menu", self.player, self.multiworld),
            "Earlier levels": Region("Earlier levels", self.player, self.multiworld),  # Always sphere 1
            "Later levels": Region("Later levels", self.player, self.multiworld),
            "Last level": Region("Last level", self.player, self.multiworld),
            "Early coins": Region("Early coins", self.player, self.multiworld),  # Always sphere 1
            "Mid coins": Region("Mid coins", self.player, self.multiworld),
            "Late coins": Region("Late coins", self.player, self.multiworld),
            "Last coins": Region("Last coins", self.player, self.multiworld),
        }

        max_level = self.options.level_locations_adjustments["Maximum"]
        self.max_level = max_level
        for i in range(1, max_level+1):
            if i == 1 or i/max_level <= 0.4:
                self.regions["Earlier levels"].locations.append(locations.VoltorbFlipLocation(
                    self.player, f"Win level {i}", i, self.regions["Earlier levels"]
                ))
            elif i == max_level:
                self.regions["Last level"].locations.append(locations.VoltorbFlipLocation(
                    self.player, f"Win level {i}", i, self.regions["Last level"]
                ))
            else:
                self.regions["Later levels"].locations.append(locations.VoltorbFlipLocation(
                    self.player, f"Win level {i}", i, self.regions["Later levels"]
                ))
        max_coins = self.options.coin_locations_adjustments["Maximum"]
        coin_steps = self.options.coin_locations_adjustments["Steps"]
        coin_regions = self.options.coin_locations_adjustments["Regions"]
        last_coin = max_coins - (max_coins % coin_steps)
        self.last_coin = last_coin

        if coin_regions != -1:
            for i in range(0, coin_regions):
                name = create_coin_region_name(i, coin_regions)
                self.regions[name] = Region(name, self.player, self.multiworld)

        def add_coin_location(region_name: str, coin_amount: int):
            self.regions[region_name].locations.append(locations.VoltorbFlipLocation(
                self.player, f"Collect {coin_amount} coins", coin_amount, self.regions[region_name]
            ))

        for i in range(coin_steps, last_coin+1, coin_steps):
            if coin_regions != 1:
                coins_per_region = (max_coins // coin_steps) // coin_regions
                region_index = i // (coin_steps + coins_per_region * coin_steps)
                add_coin_location(create_coin_region_name(region_index, coin_regions), i)

            elif i == coin_steps:
                add_coin_location("Early coins", i)
            elif i == last_coin:
                add_coin_location("Last coins", i)
            elif i <= 1000:
                add_coin_location("Early coins", i)
            elif i <= last_coin//2:
                add_coin_location("Mid coins", i)
            else:
                add_coin_location("Late coins", i)
        self.multiworld.regions.extend(self.regions.values())

    def create_items(self) -> None:
        if self.options.artificial_logic == "off":
            self.luck_classification = ItemClassification.filler
        for _ in range(sum(len(reg.locations) for reg in self.regions.values())):
            self.multiworld.itempool.append(self.create_item("Luck"))

    def set_rules(self) -> None:
        self.regions["Menu"].connect(self.regions["Earlier levels"], "Earlier levels")
        self.regions["Menu"].connect(self.regions["Early coins"], "Early coins")
        if create_coin_region_name(0) in self.regions:
            self.regions["Menu"].connect(self.regions[create_coin_region_name(0)], create_coin_region_name(0))
        if self.options.artificial_logic == "experimental" and not settings.get_settings()["voltorb_flip_settings"]["allow_experimental_logic"]:
            import logging
            logging.warning("Experimental logic was disabled in host settings, so it will be reverted to non-experimental for player "+self.player_name+".")
            self.options.artificial_logic.value = 1
        if self.options.artificial_logic == "experimental":
            self.options.progression_balancing.value = 0  # Reduces rate of generation failures
            if not VoltorbFlipWorld.progression_list:
                VoltorbFlipWorld.progression_list.extend([
                    (item.name, item.player)
                    for item in self.multiworld.itempool
                    if ItemClassification.progression in item.classification
                ])
            custom_coin_regions = self.options.coin_locations_adjustments["Regions"]
            if custom_coin_regions == -1:
                coin_regions = 3
            else:
                coin_regions = custom_coin_regions

            items = [self.random.choice(VoltorbFlipWorld.progression_list) for _ in range(2 + coin_regions)]
            print(items)
            self.regions["Earlier levels"].connect(self.regions["Later levels"], "Later levels", lambda state: state.has(items[0][0], items[0][1]))
            self.regions["Later levels"].connect(self.regions["Last level"], "Last level", lambda state: state.has(items[1][0], items[1][1]))

            if custom_coin_regions == -1:
                self.regions["Early coins"].connect(self.regions["Mid coins"], "Mid coins", lambda state: state.has(items[2][0], items[2][1]))
                self.regions["Mid coins"].connect(self.regions["Late coins"], "Late coins", lambda state: state.has(items[3][0], items[3][1]))
                self.regions["Late coins"].connect(self.regions["Last coins"], "Last coins", lambda state: state.has(items[4][0], items[4][1]))
            else:
                for i in range(0, custom_coin_regions):
                    self.regions[create_coin_region_name(i, coin_regions)].connect(
                        self.regions[create_coin_region_name(i + 1, coin_regions)], create_coin_region_name(i + 1, coin_regions),
                        lambda state: state.has(items[i + 2][0], items[i + 2][1])
                    )
        elif self.options.artificial_logic == "on":
            count = sum(len(reg.locations) for reg in self.regions.values())
            self.regions["Earlier levels"].connect(self.regions["Later levels"], "Later levels", lambda state: state.has("Luck", self.player, 1))
            self.regions["Later levels"].connect(self.regions["Last level"], "Last level", lambda state: state.has("Luck", self.player, count//2))
            self.regions["Early coins"].connect(self.regions["Mid coins"], "Mid coins", lambda state: state.has("Luck", self.player, 1))
            self.regions["Mid coins"].connect(self.regions["Late coins"], "Late coins", lambda state: state.has("Luck", self.player, max(1, count//5)))
            self.regions["Late coins"].connect(self.regions["Last coins"], "Last coins", lambda state: state.has("Luck", self.player, count//2))
        else:
            self.regions["Earlier levels"].connect(self.regions["Later levels"], "Later levels")
            self.regions["Later levels"].connect(self.regions["Last level"], "Last level")
            self.regions["Early coins"].connect(self.regions["Mid coins"], "Mid coins")
            self.regions["Mid coins"].connect(self.regions["Late coins"], "Late coins")
            self.regions["Late coins"].connect(self.regions["Last coins"], "Last coins")
        if self.options.goal == "levels":
            self.multiworld.completion_condition[self.player] = lambda state: state.can_reach_location(f"Win level {self.max_level}", self.player)
        else:
            self.multiworld.completion_condition[self.player] = lambda state: state.can_reach_location(f"Collect {self.last_coin} coins", self.player)
        self.regions.clear()

    def fill_slot_data(self) -> Mapping[str, Any]:
        return {
            "goal": self.options.goal.current_key,
            "level_locations_adjustments": self.options.level_locations_adjustments.value,
            "coin_locations_adjustments": self.options.coin_locations_adjustments.value,
        }


class VoltorbFlipItem(Item):
    game = "Voltorb Flip"
