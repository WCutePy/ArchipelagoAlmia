from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import CollectionState
from worlds.generic.Rules import add_rule, set_rule
from .data import data, ItemCategory

if TYPE_CHECKING:
    from .world import PokemonRSOA


def set_all_rules(world: PokemonRSOA) -> None:
    set_all_entrance_rules(world)
    set_all_location_rules(world)
    set_completion_condition(world)


def set_all_entrance_rules(world: PokemonRSOA) -> None: ...


def set_all_location_rules(world: PokemonRSOA) -> None: ...


def set_completion_condition(world) -> None:

    def has_n_checks(state: CollectionState, n: int) -> bool:
        return state.has_from_list(
            [
                item.label
                for item in data.items.values()
                if ItemCategory.STYLER_UPGRADE in item.item_categories
            ],
            world.player,
            n,
        )

    captures = world.options.capture_count_target.value
    completion_condition = lambda state: has_n_checks(state, captures)

    world.multiworld.completion_condition[world.player] = completion_condition
