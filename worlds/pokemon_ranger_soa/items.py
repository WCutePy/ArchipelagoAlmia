from __future__ import annotations

from typing import Dict, FrozenSet, Optional, TYPE_CHECKING, List, Tuple

from BaseClasses import ItemClassification, Item
from .data import data, BASE_OFFSET, ItemCategory

if TYPE_CHECKING:
    from .world import PokemonRSOA


class PokemonRSOAItem(Item):
    game: str = "PokemonRangerSOA"
    tags: Tuple[ItemCategory]

    def __init__(
        self,
        name: str,
        classification: ItemClassification,
        code: Optional[int],
        player: int,
    ) -> None:
        super().__init__(name, classification, code, player)

        if code is None:
            self.tags = (ItemCategory.EVENT,)
        else:
            self.tags = data.items[reverse_offset_item_value(code)].item_categories


def offset_item_value(item_value: int) -> int:
    """
    Returns the AP item id (code) for a given item value
    """
    return item_value + BASE_OFFSET


def reverse_offset_item_value(item_id: int) -> int:
    """
    Returns the item value for a given AP item id (code)
    """
    return item_id - BASE_OFFSET


def create_item_label_to_code_map() -> Dict[str, int]:
    """
    Creates a map from item labels to their AP item id (code)
    """
    label_to_code_map: Dict[str, int] = {}
    for item_value, attributes in data.items.items():
        label_to_code_map[attributes.label] = offset_item_value(item_value)

    label_to_code_map["Filler Item"] = offset_item_value(10000)

    print(data.items)

    return label_to_code_map


def get_item_classification(item_code: int) -> ItemClassification:
    """
    Returns the item classification for a given AP item id (code)
    """
    return data.items[reverse_offset_item_value(item_code)].classification


def create_item_with_correct_classification(
    world: PokemonRSOA, name: str
) -> PokemonRSOAItem:
    item_id = world.item_name_to_id[name]
    offset_id = reverse_offset_item_value(item_id)
    classification = data.items[offset_id].classification

    return PokemonRSOAItem(name, classification, item_id, world.player)


def create_all_items(world: PokemonRSOA) -> None:

    itempool: List[Item] = []

    number_of_items = len(itempool)
    number_of_unfilled_locations = len(
        world.multiworld.get_unfilled_locations(world.player)
    )

    needed_number_of_filler_items = number_of_unfilled_locations - number_of_items

    created = 0
    for i, item in data.items.items():
        if ItemCategory.STYLER_UPGRADE in item.item_categories:

            for j in range(item.copies):
                if created >= needed_number_of_filler_items:
                    break

                new_item = world.create_item(item.label)
                itempool.append(new_item)
                created += 1

        if created >= needed_number_of_filler_items:
            break

    while created < needed_number_of_filler_items:

        item = world.create_filler()
        itempool.append(item)

        created += 1
    world.multiworld.itempool += itempool
