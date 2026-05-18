from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict

from BaseClasses import CollectionState, Entrance, Location, ItemClassification
from worlds.generic.Rules import add_rule, set_rule

from rule_builder.options import OptionFilter
from rule_builder.rules import Has, Rule, HasAllCounts
from .data import data, ItemCategory, FieldMove
from .items import PokemonRSOAItem
from .locations import PokemonRSOALocation

if TYPE_CHECKING:
    from .world import PokemonRSOA


def get_entrance(world: PokemonRSOA, entrance: str) -> Entrance:
    return world.multiworld.get_entrance(entrance, world.player)


def get_pokemon_instance(world: PokemonRSOA, instance_name: str) -> Entrance:
    return get_entrance(world, instance_name)


def get_location(world: PokemonRSOA, location: str) -> Location:
    if location in data.locations:
        location = data.locations[location].label

    return world.multiworld.get_location(location, world.player)


def can_destroy_target_type(state, world: PokemonRSOA, target: int):
    """
    The int of the target
    """
    field_move = data.target_field_move_requirements[target].to_event()
    return Has(field_move)


def set_all_rules(world: PokemonRSOA) -> None:
    field_move_rules: Dict[FieldMove, Rule] = {}
    for i, pokemon in data.species.items():

        world.set_rule(
            get_location(world, pokemon.location_capture_name),
            Has(pokemon.event_add_to_browser),
        )

        start_level = pokemon.field_move.level

        for j in range(1, start_level + 1):
            field_move = FieldMove(category=pokemon.field_move.category, level=j)
            current_rule = field_move_rules.get(field_move, None)
            if current_rule is None:
                field_move_rules[field_move] = Has(pokemon.event_can_capture)
            else:
                field_move_rules[field_move] |= Has(pokemon.event_can_capture)

    field_move_region = world.get_region("Overworld")
    for field_move, pokemon_rules in field_move_rules.items():
        field_move_rule = pokemon_rules & Has(
            field_move.category.item_name,
            1,
            # options=[
            #     OptionFilter(
            #         world.options.field_move_item,
            #         world.options.field_move_item.option_vanilla,
            #         "ne",
            #     )
            # ],
            # filtered_resolution=True,
        )
        field_move_rule = pokemon_rules

        field_move_location = PokemonRSOALocation(
            world.player, field_move.event_can_use_field_move, None, field_move_region
        )
        field_move_location.show_in_spoiler = False

        field_move_location.place_locked_item(
            PokemonRSOAItem(
                field_move.event_can_use_field_move,
                ItemClassification.progression_skip_balancing,
                None,
                world.player,
            )
        )

        world.set_rule(field_move_location, field_move_rule)
        field_move_region.locations.append(field_move_location)

    set_tutorial_rules(world)

    set_completion_condition(world)


def set_tutorial_rules(world: PokemonRSOA) -> None:
    pass


def set_completion_condition(world) -> None:
    def captured_n_pokemon(state: CollectionState, n: int) -> bool:
        return state.has_from_list_unique(
            [i.event_add_to_browser for i in data.species.values()], world.player, n
        )

    captures = world.options.capture_count_target.value
    completion_condition = lambda state: captured_n_pokemon(state, captures)

    world.multiworld.completion_condition[world.player] = completion_condition
