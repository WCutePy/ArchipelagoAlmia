from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Union, Optional, List, TypeAlias, Iterable

from narwhals import exclude

from BaseClasses import CollectionState, Entrance, Location, ItemClassification
from worlds.generic.Rules import add_rule, set_rule

from rule_builder.options import OptionFilter
from rule_builder.rules import (
    Has,
    Rule,
    HasAllCounts,
    True_,
    CanReachLocation,
    CanReachRegion, False_,
)
from .data import data, ItemCategory, FieldMove
from .events import (
    PREvent,
    get_instance_base,
    get_instance_capture,
    get_instance_target,
    get_loading_zone_name,
    get_instance_browser,
    PInstanceEvent,
)
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
    return get_entrance(world, get_loading_zone_name(from_, to))


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


MonSelect: TypeAlias = Optional[Dict[str, Optional[Iterable[int]]]]


def access_field_move(
    world: PokemonRSOA,
    field_move: FieldMove,
    include: MonSelect = None,
    exclude: MonSelect = None,
    include_one_time: bool = False,
) -> Rule:
    pokemon_rules = True_()
    for region_name, region_data in data.regions.items():
        exclude_region = True if exclude is None else exclude.get(region_name, True)
        if exclude and (
            not exclude_region
            or any(region_name.startswith(e) for e in exclude if "_" not in e)
        ):
            continue
        if exclude_region is True:
            exclude_region = []
        include_region = None if include is None else include.get(region_name, None)
        if include and (
            include_region is None
            or any(region_name.startswith(i) for i in include if "_" not in i)
        ):
            continue

        for i, spawn_data in region_data.POKEMON_SPAWN.items():
            if exclude and i in exclude_region:
                continue
            if include and (not include_region or i not in include_region):
                continue

            if not include_one_time and spawn_data.one_time:
                continue

            species = data.form_id_to_species[spawn_data.SPECIES_ID]
            if species.field_move.satisfies(field_move):
                if include_one_time:
                    pokemon_rules |= CanReachLocation(
                        get_instance_browser(region_name, i)
                    )
                else:
                    pokemon_rules |= CanReachLocation(
                        get_instance_capture(region_name, i)
                    )
    return pokemon_rules


def can_destroy_target(
    world: PokemonRSOA,
    map_name: Union[str, int],
    i: int,
    include: MonSelect = None,
    exclude: MonSelect = None,
    include_one_time: bool = False,
) -> Rule:
    """
    TODO, reconsider if it's necessary to have a field move restriction to target events
    and instead handle it here fully, for now leaving as is, some minor duplication of
    logic is here right now, as being able to use field move item is inhernt from
    Has(target)

    MUST be exhausted directly, as include and exclude are expected to be expanded over
    its use
    """
    map_name = sanitize_map_name(map_name)
    target = get_instance_target(map_name, i)

    field_move = data.target_field_move_requirements[
        data.regions[map_name].TARGETS[str(i)].TARGET_ID
    ]

    if include is None and exclude is None:
        return Has(field_move.event_can_use_field_move)

    return has_field_move_item(field_move) & access_field_move(
        world, field_move, include, exclude, include_one_time
    )


def can_destroy_target_type(
    world: PokemonRSOA,
    target_id: int,
    include: MonSelect = None,
    exclude: MonSelect = None,
    include_one_time: bool = False,
) -> Rule:
    """
    The int of the target

    any len 0 iterable in MonSelect evaluates to the whole map.
    any len >=1 iterable accounts only the specified members in the iterable
    """
    field_move: FieldMove = data.target_field_move_requirements[target_id]

    if include is None and exclude is None:
        return Has(field_move.event_can_use_field_move)

    return has_field_move_item(field_move) & access_field_move(
        world, field_move, include, exclude, include_one_time
    )


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
    set_mission_1_and_2_rules(world)

    set_completion_condition(world)


def set_tutorial_rules(world: PokemonRSOA) -> None:

    world.set_rule(
        get_pokemon_instance(world, "m001_002", 7),
        can_destroy_target(world, "m001_002", 3),
    )

    for i in [6, 12]:
        world.set_rule(
            get_pokemon_instance(world, "m001_002", i),
            False_()
        )
    world.set_rule(
        get_connection(world, "m001_002", "m001_014"),
        False_()
    )

    """School first night"""
    # TODO when randomizing this only has access to indoor pokemon
    school_night_include = {
        "m001_003a": [],
        "m001_004": [],
        "m001_006": [],
        "m001_007": [],
        "m001_008": [],
        "m001_011": [],
    }
    world.set_rule(
        get_pokemon_instance(world, "m001_004", 0),
        can_destroy_target_type(
            world, 27, include=school_night_include, include_one_time=True
        ),  # crate
    )

    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_007", i),
            can_destroy_target_type(
                world, 27, include=school_night_include, include_one_time=True
            ),  # crate
        )

    world.set_rule(
        get_location(world, PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        can_destroy_target_type(
            world, 27, include=school_night_include, include_one_time=True
        ),  # crate
    )

    # basement access
    for from_ in ["m001_003a", "m001_003b"]:
        world.set_rule(
            get_connection(world, from_, "m001_011"),
            Has(PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        )
    world.set_rule(
        get_location(world, PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        can_destroy_target_type(
            world, 27, include=school_night_include, include_one_time=True
        )
        & can_destroy_target_type(
            world, 37, include=school_night_include, include_one_time=True
        ),  # crate
    )

    world.set_rule(
        get_pokemon_instance(world, "m001_011", 4),
        can_destroy_target_type(
            world, 27, include=school_night_include, include_one_time=True
        ),  # crate
    )
    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_011", i),
            Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        )

    world.set_rule(
        get_pokemon_instance(world, "m001_007", 5),
        False_()
    ) # TODO figure out when separate ghastly spawns

    """School day 3"""

    # and specify the available mons

    # TODO, swap over to an exclusion ("out of logic" ship is not accounted for now for acces), expand when known how to permanently return to school
    include_og = {
        "m001_002": [],
        "m001_003a": [], # quite sure all are available
        "m001_005": [],
        "m001_009": [],
        "m001_011": [],
        "m001_001": [0, 1, 2, 5],
        "m001_015": [],
    }

    world.set_rule(
        get_pokemon_instance(world, "m001_009", 0),
        Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
    )
    world.set_rule(
        get_connection(world, "m001_005", "m001_016"),
        (Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name)
        & can_destroy_target(world, "m001_005", 1, include=include_og)) | False_(),
    ) # TODO if acquired early, allows for sequence break by moving to cargo ship that allows crash

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
            can_destroy_target(world, "m001_001", 5, include=include_og) | False_(),
        )

    world.set_rule(
        get_connection(world, "m001_001", "m001_015"),
        can_destroy_target(world, "m001_001", 0, include=include_og) | False_(),
    )

    """School day 3 - leave school oneway"""

    for from_, to in [("m004_001", "m009_002"), ("m008_001", "m039_012"), ("m008_003", "m017_007"),]:
        world.set_rule(get_connection(world, from_, to), False_())

    # TODO figure out what the full scope for the tree in chicole will be before potential bk
    world.set_rule(
        get_pokemon_instance(world, "m007_001", 4),
        can_destroy_target(world, "m007_001", 1),  # tree
    )

    # maybe consider making an event
    mission_0 = data.locations["MISSION_00"].label
    world.set_rule(
        get_location(world, mission_0),
        CanReachRegion(data.regions["m005_001a"].HUMAN_NAME),
    )

    world.set_rule(
        get_entrance(world, PInstanceEvent.TANGROWTH.event_name),
        CanReachRegion(data.regions["m005_001a"].HUMAN_NAME),
    )

    for from_ in ["m001_002", "m001_003a", "m001_004", "m001_006", "m001_007", "m001_008", "m001_009", "m001_011"]:
        world.set_rule(
            get_connection(world, from_, "m001_003b"),
            CanReachRegion(data.regions["m005_001a"].HUMAN_NAME)
        )


def set_mission_1_and_2_rules(world: PokemonRSOA):
    mission_1 = data.locations["MISSION_01"].label
    world.set_rule(
        get_location(world, mission_1),
        CanReachLocation(data.locations["MISSION_00"].label),
    )

    # m005_001b is reached without requiring rules based on
    # the only way to leave school and no obstacles in the way
    # only missions, thus indirect

    """Mission 2 - Investigate the Marine Cave!"""
    """Marine cave"""
    include = {
        "m001_001": [3, 4],
        "m005_001b": [],
        "m007_001": [],
        "m006_002": [],  # unreachable until a bit later
        "m006_003": [],  # unreachable until a bit later
        "m006_004": [],  # unreachable until a bit later
    }

    can_destroy_wooden_gate = can_destroy_target(
        world, "m006_001", 2, include=include
    ) | can_destroy_target(world, "m006_001", 3, include=include)

    world.set_rule(
        get_connection(world, "m006_001", "m006_002"), can_destroy_wooden_gate
    )
    world.set_rule(
        get_connection(world, "m006_001", "m006_003"),
        can_destroy_wooden_gate
        & can_destroy_target(world, "m006_001", 1, include=include),
    )

    world.set_rule(
        get_location(world, get_instance_target("m006_001", 0)),
        can_destroy_wooden_gate
        & can_destroy_target(world, "m006_001", 0, include=include),  # red gigaremo
    )

    for i in range(7):
        world.set_rule(
            get_location(world, get_instance_capture("m006_001", i)),
            Has(get_instance_target("m006_001", 0)),
        )  # only 2 zubats at first, after mission 2 complete the rest

        if i in [5, 6]:
            continue
        world.set_rule(
            get_pokemon_instance(world, "m006_001", i),
            can_destroy_wooden_gate,
        )

    world.set_rule(
        get_connection(world, "m006_002", "m006_004"),
        can_destroy_target(world, "m006_002", 0, include=include),  # rock crush 2
    )

    mission_2 = data.locations["MISSION_02"].label
    world.set_rule(
        get_location(world, mission_2), Has(get_instance_target("m006_001", 0))
    )

    quest_1 = data.locations["QUEST_01"].label
    world.set_rule(get_location(world, quest_1), CanReachLocation(mission_2))
    world.set_rule(
        get_entrance(world, PInstanceEvent.MILTANK.event_name),
        CanReachLocation(quest_1),
    )  # not possible if goal is mission 2

    """blacklist connections past goal"""

    # world.set_rule(
    #     # get_pokemon_instance(world, "m001_001", 0),
    #     get_location(world, "CAPTURE_Croagunk"),
    #     False_()
    # )

    # world.set_rule(
    #     get_location(world, data.species[1].location_capture_name),
    #     False_()
    # )
    #
    # world.set_rule(
    #     get_entrance(world, PInstanceEvent.CHIMCHAR.event_name),
    #     False_()
    # )
    #
    # world.set_rule(
    #     get_pokemon_instance(world, "m001_001", 0),
    #     False_()
    # )


def set_completion_condition(world) -> None:
    def captured_n_pokemon(state: CollectionState, n: int) -> bool:
        return sum(state.can_reach_location(s.location_capture_name, world.player) for s in data.species.values()) >= n

    # def captured_n_pokemon(state: CollectionState, n: int) -> bool:
    #     return state.has_from_list_unique(
    #         [i.event_add_to_browser for i in data.species.values()], world.player, n
    #     )

    captures = world.options.capture_count_target.value
    captures = 21
    completion_condition = lambda state: captured_n_pokemon(state, captures)

    world.multiworld.completion_condition[world.player] = completion_condition
