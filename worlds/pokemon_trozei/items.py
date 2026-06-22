from __future__ import annotations


from typing import TYPE_CHECKING, Dict, List, Tuple, Set, Optional

from BaseClasses import Region, Location, Item, ItemClassification
from . import data

if TYPE_CHECKING:
    from .world import PokemonTrozei


class PokemonTrozeiItem(Item):
    game: str = "PokemonTrozei"

    def __init__(
        self,
        name: str,
        classification: ItemClassification,
        code: Optional[int],
        player: int,
    ) -> None:
        super().__init__(name, classification, code, player)


def create_item_label_to_code_map():
    items = {}
    for i, stage in enumerate(data.stages, start=1):
        items[stage.unlock_name] = i
    assert i < 100

    items["Coin x1"] = 100
    items["Coin x3"] = 101
    items["Coin x5"] = 102

    return items


def get_item_classification(item_code: int) -> ItemClassification:
    """
    Returns the item classification for a given AP item id (code)
    """
    if item_code < 100:
        return ItemClassification.progression_skip_balancing
    if item_code < 102:
        return ItemClassification.filler
    if item_code == 102:
        return ItemClassification.useful

    return ItemClassification.filler


def create_item_with_correct_classification(
    world: PokemonTrozei, name: str
) -> PokemonTrozeiItem:
    item_id = world.item_name_to_id[name]
    classification = get_item_classification(item_id)

    return PokemonTrozeiItem(name, classification, item_id, world.player)


def create_all_items(world: PokemonTrozei) -> None:

    itempool: List[Item] = []
    precollected_stages = [0]

    # for i, stage in enumerate(data.stages):
    for i in [0, 5, 1, 2, 6, 7, 30]:
        stage = data.stages[i]
        new_item = world.create_item(stage.unlock_name)
        if i in precollected_stages:
            world.push_precollected(new_item)
        else:
            itempool.append(new_item)

    number_of_items = len(itempool)
    number_of_unfilled_locations = len(world.multiworld.get_unfilled_locations(world.player))

    needed_filler = number_of_unfilled_locations - number_of_items

    while needed_filler > 0:
        item = world.create_filler()
        itempool.append(item)

        needed_filler -= 1

    world.multiworld.itempool += itempool