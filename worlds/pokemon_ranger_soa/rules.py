from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Union, Optional, List, TypeAlias, Iterable

from BaseClasses import CollectionState, Entrance, Location, ItemClassification
from worlds.generic.Rules import add_rule, set_rule

from rule_builder.options import OptionFilter
from rule_builder.rules import Has, Rule, HasAllCounts, True_, CanReachLocation
from .data import data, ItemCategory, FieldMove
from .events import PREvent, get_instance_base, get_instance_capture
from .items import PokemonRSOAItem
from .locations import PokemonRSOALocation
from .options import FieldMoveItem

if TYPE_CHECKING:
    from .world import PokemonRSOA


def sanitize_map_name(map_name: Union[str, int]) -> str:
    if isinstance(map_name, int):
        map_name = data.map_id_to_region_name[map_name]
    elif map_name.lower().startswith("0x"):
        map_name = data.map_id_to_region_name[int(map_name, 16)]
    return map_name


def get_entrance(world: PokemonRSOA, entrance: str) -> Entrance:
    return world.multiworld.get_entrance(entrance, world.player)


def get_connection(
    world: PokemonRSOA, from_: Union[str], to: Union[str, int]
) -> Entrance:
    from_ = sanitize_map_name(from_)
    to = sanitize_map_name(to)
    return get_entrance(world, f"{from_} -> {to}")


def get_pokemon_instance(
    world: PokemonRSOA, map_name: Union[str, int], i: int
) -> Entrance:
    map_name = sanitize_map_name(map_name)
    instance_name = get_instance_base(map_name, i)
    return get_entrance(world, instance_name)


def get_location(world: PokemonRSOA, location: str) -> Location:
    if location in data.locations:
        location = data.locations[location].label

    return world.multiworld.get_location(location, world.player)


def can_destroy_target(map_name: Union[str, int], i: int) -> Rule:
    if isinstance(map_name, int):
        map_name = data.map_id_to_region_name[map_name]
    elif map_name.lower().startswith("0x"):
        map_name = data.map_id_to_region_name[int(map_name, 16)]
    field_move = f"{map_name}.T.{i}"
    return Has(field_move)


def can_destroy_target_type(target_id: int) -> Rule:
    """
    The int of the target
    """
    field_move = data.target_field_move_requirements[target_id].event_can_use_field_move
    return Has(field_move)


MonSelect: TypeAlias = Optional[Dict[str, Optional[Iterable[int]]]]
def can_destroy_target_new(world: PokemonRSOA, map_name: Union[str, int], i: int) -> Rule:
    if isinstance(map_name, int):
        map_name = data.map_id_to_region_name[map_name]
    elif map_name.lower().startswith("0x"):
        map_name = data.map_id_to_region_name[int(map_name, 16)]
    target = f"{map_name}.T.{i}"
    return Has(target)


def can_destroy_target_type_new(world: PokemonRSOA, target_id: int, include: MonSelect=None, exclude: MonSelect=None) -> Rule:
    """
    The int of the target

    any len 0 iterable in MonSelect evaluates to the whole map.
    any len >=1 iterable accounts only the specified members in the iterable
    """
    field_move: FieldMove = data.target_field_move_requirements[target_id]

    if include is None and exclude is None:
        return Has(field_move.event_can_use_field_move)

    pokemon_rules = True_
    for region_name, region_data in data.regions.items():
        exclude_region = exclude.get(region_name, True)
        if exclude and not exclude_region: continue
        if exclude_region is True: exclude_region = []
        include_region = include.get(region_name, None)
        if include and include_region is None:
            continue

        for i, spawn_data in region_data.POKEMON_SPAWN.items():
            if exclude and i in exclude_region: continue
            if include and (not include_region or i not in include_region): continue

            species = data.form_id_to_species[spawn_data.SPECIES_ID]
            if species.field_move.satisfies(field_move):
                pokemon_rules |= CanReachLocation(get_instance_capture(region_name, i))

    return has_field_move_item(field_move) & pokemon_rules


def has_field_move_item(field_move: FieldMove) -> Rule:
    return Has(
        field_move.category.item_name,
        1,
        options=[
            OptionFilter(
                FieldMoveItem,
                FieldMoveItem.option_vanilla,
            )
        ],
        filtered_resolution=True,
    )


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

    for field_move, pokemon_rules in field_move_rules.items():
        field_move_rule = pokemon_rules & has_field_move_item(field_move)

        field_move_location = get_location(world, field_move.event_can_use_field_move)
        world.set_rule(field_move_location, field_move_rule)

    set_tutorial_rules(world)

    set_completion_condition(world)


def set_tutorial_rules(world: PokemonRSOA) -> None:
    world.set_rule(
        get_pokemon_instance(world, "m001_002", 7), can_destroy_target("m001_002", 3)
    )

    """School first night"""
    # TODO when randomizing this only has access to indoor pokemon
    world.set_rule(
        get_pokemon_instance(world, "m001_004", 0), can_destroy_target_type(27)  # crate
    )

    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_007", i),
            can_destroy_target_type(27),  # crate
        )

    world.set_rule(
        get_location(world, PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        can_destroy_target_type(27),  # crate
    )

    # basement access
    world.set_rule(
        get_connection(world, "m001_003a", "m001_011"),
        Has(PREvent.SCHOOL_COLLECT_STYLERS.event_name),
    )
    world.set_rule(
        get_location(world, PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        can_destroy_target_type(27) & can_destroy_target_type(37),  # crate
    )

    world.set_rule(
        get_pokemon_instance(world, "m001_011", 4), can_destroy_target_type(27)  # crate
    )
    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_011", i),
            Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        )

    """School day 3"""

    world.set_rule(
        get_connection(world, "m001_005", "m001_016"),
        Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name)
        & can_destroy_target("m001_005", 1),
    )
    # TODO if acquired early, allows for sequence break by moving to cargo ship that allows crash
    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_005", i),
            Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        )

    world.set_rule(
        get_connection(world, "m001_002", "m001_001"),
        Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
    )
    for name in [get_instance_capture("m001_001", 5)]:
        world.set_rule(
            get_location(world, name),
            can_destroy_target("m001_001", 5),
        )

    world.set_rule(
        get_connection(world, "m001_001", "m001_015"),
        can_destroy_target("m001_001", 0),
    )


def set_completion_condition(world) -> None:
    def captured_n_pokemon(state: CollectionState, n: int) -> bool:
        return state.has_from_list_unique(
            [i.event_add_to_browser for i in data.species.values()], world.player, n
        )

    captures = world.options.capture_count_target.value
    completion_condition = lambda state: captured_n_pokemon(state, captures)

    world.multiworld.completion_condition[world.player] = completion_condition
