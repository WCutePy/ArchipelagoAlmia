from __future__ import annotations

import logging
import math
from typing import Dict, Optional, TYPE_CHECKING, List, Tuple

from BaseClasses import ItemClassification, Item
from Options import OptionError
from .data import (
    data,
    BASE_OFFSET,
    FieldMoveCategory,
    VANILLA_PARTNERS_FORMS_UNLOCK_ORDER,
)
from .data_dir.items import ItemCategory
from .options import StylerModelItem, LevelUpItem, RankUpItem

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


def create_all_items(world: PokemonRSOA) -> List[Item]:
    """
    some estimates to reference on early goals for vanilla vs non vanilla
    with field moves turned on

    goal: 2
    locations: 20, field_moves: 5
    goal: 3
    locations: 32, field_moves: 6
    goal: 4
    locations: 50, field_moves: 9
    goal: 5
    locations: 61, field_moves: 10
    goal: 16
    locations: 267, field_moves: 37

    random mons
    goal: 2
    locations: 57, field_moves: 5
    goal: 3
    locations: 89, field_moves: 6
    goal: 16
    locations: 308, field_moves: 37

    bidoof mostly
    goal: 3
    locations: 14, field_moves: 6
    """

    number_of_unfilled_locations = len(
        world.multiworld.get_unfilled_locations(world.player)
    ) - len(world.capture_groups)
    itempool: List[Item] = []

    itempool_full = lambda: number_of_unfilled_locations <= len(itempool)

    """field moves
    always paid for by the seeded / required mons for new field moves
    """
    if world.options.field_move_item != world.options.field_move_item.option_vanilla:
        for i, item in data.items.items():
            if ItemCategory.FIELD_MOVE not in item.item_categories:
                continue
            copies = world.field_move_stages.get(
                FieldMoveCategory(item.item_id - 10000), None
            )
            if copies is None:
                continue
            for _ in range(len(copies) + 1):
                new_item = world.create_item(item.label)
                itempool.append(new_item)

    number_of_items = len(itempool)

    print("--- items ---")
    print(
        f"goal: {world.options.mission_clear_target.value}\nlocations: {number_of_unfilled_locations}, field_moves: {number_of_items}"
    )
    print("--- ---")

    """partner - 0 to 16 items"""
    """runs at a deficit of 1 - 3 checks"""
    still_possible = []
    if world.options.partner_sanity:
        amounts = {
            5: 2,
            6: 2,
            7: 4,
            8: 5,
            9: 6,
            10: 7,
            11: 8,
            12: 9,
            13: 9,
            14: 11,
            15: 11,
            16: 11,
        }
        if not world.options.randomize_partners:
            partner_options = VANILLA_PARTNERS_FORMS_UNLOCK_ORDER
        else:
            partner_options = world.modified_partners[3:] + world.modified_partners[:3]
        amount = amounts.get(world.get_rule_num(), 0)
        for i in range(0, amount):
            label = data.items[partner_options[i] + 100].label
            new_item = world.create_item(label)
            itempool.append(new_item)
        still_possible += partner_options[amount:]

    """capture cards - 0 to many"""
    """paid for by the quests"""
    capture_card_options = []
    if world.options.capture_card_sanity:
        amounts = {
            3: 2,
            4: 6,
            5: 7,
            6: 10,
            7: 13,
            8: 13,
            9: 18,
            10: 20,
            11: 23,
            12: 26,
            13: 26,
            14: 28,
            15: 32,
            16: 32,
        }
        for i in range(1, 26):
            item = data.items[i]
            capture_card_options += [item.label for _ in range(item.copies)]
        amount = amounts.get(world.get_rule_num(), 0)
        chosen = world.random.sample(capture_card_options, amount)
        for label in chosen:
            capture_card_options.remove(label)
            new_item = world.create_item(label)
            itempool.append(new_item)
        still_possible += capture_card_options

    """styler - 1 item"""
    if world.options.styler_model_item != StylerModelItem.option_vanilla:
        styler = world.create_item("Progressive Styler")
        world.push_precollected(styler)

        itempool.append(world.create_item("Progressive Styler"))

    """rank - 0-4 items"""
    """starting from mission 5 all rank ups are in the game"""
    if world.options.rank_up_item == RankUpItem.option_item:
        for i in range(min(4, max(0, world.get_rule_num() - 1))):
            new_item = world.create_item("Progressive Rank")
            itempool.append(new_item)
    # elif world.options.rank_up_item == RankUpItem.option_item_all:
    #     to_create["Progressive Rank"] = 10

    """level up items 0 - 198 items"""
    if world.options.level_up_item.value:
        original_percent = world.options.level_up_percent.value
        while True:
            remaining = number_of_unfilled_locations - len(itempool)
            max_level = world.options.level_up_max
            percent = world.options.level_up_percent

            amount_per_item = max_level * (percent / 100)
            each = math.ceil(max_level / amount_per_item)
            total = each * (
                1 + (world.options.level_up_item == LevelUpItem.option_separate)
            )
            if (remaining - total) < min(10, remaining):
                world.options.level_up_percent.value += 2
                if world.options.level_up_percent > 100:
                    raise OptionError(
                        f"Player {world.player} has not enough locations to "
                        f"support level_up_item as {world.options.level_up_item}"
                    )
            else:
                break

        if original_percent != world.options.level_up_percent:
            logging.warning(
                f"Player {world.player} level_up_percent adjusted from "
                f"{original_percent}% to {world.options.level_up_percent.value}%."
                f" Each now gives an increase of {math.ceil(amount_per_item)}."
            )

        if world.options.level_up_item == LevelUpItem.option_separate:
            items = ["Progressive Power", "Progressive Energy"]
        else:
            items = ["Progressive Level"]

        for label in items:
            for i in range(each):
                new_item = world.create_item(label)
                itempool.append(new_item)

    # if

    limited_filler = ["Vatonage Styler"]

    world.random.shuffle(limited_filler)
    for label in limited_filler:
        item = world.create_item(label)
        itempool.append(item)
        if itempool_full():
            print("hi itempool full")
            return itempool

    world.random.shuffle(still_possible)
    for label in still_possible:
        item = world.create_item(label)
        itempool.append(item)
        if itempool_full():
            return itempool

    print("hello", itempool_full, len(itempool))
    while not itempool_full():
        item = world.create_filler()
        itempool.append(item)

    return itempool
