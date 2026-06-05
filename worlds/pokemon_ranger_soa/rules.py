from __future__ import annotations

from collections import defaultdict
from dataclasses import field, dataclass
from typing import (
    TYPE_CHECKING,
    Dict,
    Union,
    Optional,
    List,
    TypeAlias,
    Iterable,
    Sized,
    ClassVar,
)

from BaseClasses import CollectionState, Entrance, Location, ItemClassification

from rule_builder.rules import (
    Has,
    Rule,
    HasAllCounts,
    True_,
    CanReachLocation,
    CanReachRegion,
    False_,
    HasFromList,
    HasFromListUnique,
)
from .data import (
    data,
    ItemCategory,
    FieldMove,
    LocationCategory,
    pokemon_to_target_id,
    FieldMoveCategory,
)
from .events import (
    PREvent,
    get_instance_base,
    get_instance_capture,
    get_instance_target,
    get_loading_zone_name,
    get_instance_browser,
    PInstanceEvent,
    get_mission_event,
    get_quest_event,
    get_instance_missable,
)
from .options import FieldMoveItem
from .MonSelect import sanitize_map_name, MonSelect, has_field_move_item

if TYPE_CHECKING:
    from .world import PokemonRSOA


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


def set_all_rules(world: PokemonRSOA) -> None:
    MonSelect.world = world
    full_map = MonSelect.get_rules_scope()

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
        field_move_rule = pokemon_rules & has_field_move_item(world, field_move)

        field_move_location = get_location(world, field_move.event_can_use_field_move)
        world.set_rule(field_move_location, field_move_rule)

    for region_name, region_data in world.modified_regions.items():
        if not full_map.region_included(region_name, region_data):
            continue

        for i, mon_data in region_data.POKEMON_SPAWN.items():
            if mon_data.SPECIES_NAME in ["Doduo", "Staraptor"]:
                world.set_rule(get_pokemon_instance(world, region_name, i), False_())

    for i in range(1, 61):
        world.set_rule(
            get_location(world, data.locations[f"QUEST_{i:02}"].label), False_()
        )
        world.set_rule(get_location(world, get_quest_event(i)), False_())

    set_tutorial_rules(world)
    # set_mission_1_and_2_rules(world)
    # set_mission_3_rules(world)
    # set_mission_4_rules(world)

    set_completion_condition(world)

    MonSelect.world = None


def set_tutorial_rules(world: PokemonRSOA) -> None:
    """
    Goal: capture cutscene Tangrowth

    Possibly reachable instances:

    missions: 1
    quests: 0
    missable_pokemon: 17
    browser_entries:
    captures:

    if ship is included
    missable_locations:
    browser_locations:
    capture_locations:
    """

    full_map = MonSelect.full_map()

    world.set_rule(
        get_pokemon_instance(world, "m001_002", 7),
        full_map.can_destroy_target("m001_002", 3)
        & full_map.can_destroy_target_type(pokemon_to_target_id("bonsly")),
    )

    for i in [6, 12]:
        world.set_rule(get_pokemon_instance(world, "m001_002", i), False_())
    world.set_rule(get_connection(world, "m001_002", "m001_014"), False_())

    """School first night"""
    school_night = MonSelect(
        include={
            "m001_003a": [],
            "m001_004": [],
            "m001_006": [],
            "m001_007": [],
            "m001_008": [],
            "m001_011": [],
        },
        include_one_time=True,
        include_missable=True,
    )
    world.set_rule(
        get_pokemon_instance(world, "m001_004", 0),
        school_night.can_destroy_target_type(27),  # crate
    )

    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_007", i),
            school_night.can_destroy_target_type(27),  # crate
        )

    world.set_rule(
        get_location(world, PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        school_night.can_destroy_target_type(27),  # crate
    )

    print(
        school_night.can_destroy_target_type(27),
    )

    # basement access
    for from_ in ["m001_003a", "m001_003b"]:
        world.set_rule(
            get_connection(world, from_, "m001_011"),
            Has(PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        )
    world.set_rule(
        get_location(world, PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        school_night.can_destroy_target_type(27)
        & school_night.can_destroy_target_type(37),  # crate
    )

    world.set_rule(
        get_pokemon_instance(world, "m001_011", 4),
        school_night.can_destroy_target_type(27),  # crate
    )
    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_011", i),
            Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        )

    world.set_rule(
        get_pokemon_instance(world, "m001_011", 5), False_()
    )  # TODO figure out when separate ghastly spawns

    """School day 3"""

    world.set_rule(
        get_pokemon_instance(world, "m001_009", 0),
        Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
    )

    for from_ in ["m001_005", "m001_014"]:
        world.set_rule(
            get_connection(world, from_, "m001_016"),
            (
                Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name)
                & full_map.can_destroy_target("m001_005", 1)
            ),
        )  # TODO if acquired early, allows for sequence break by moving to cargo ship that allows crash

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
            full_map.can_destroy_target("m001_001", 5),
        )

    world.set_rule(
        get_connection(world, "m001_001", "m001_015"),
        full_map.can_destroy_target("m001_001", 0),
    )

    """School day 3 - leave school oneway"""

    for from_, to in [
        ("m004_001", "m009_002"),
        ("m008_001", "m039_012"),
        ("m008_003", "m017_007"),
    ]:
        world.set_rule(get_connection(world, from_, to), False_())

    # TODO figure out what the full scope for the tree in chicole will be before returning to school.

    world.set_rule(
        get_pokemon_instance(world, "m007_001", 4),
        full_map.can_destroy_target("m007_001", 1),  # tree
    )

    # maybe consider making an event
    # mission_0 = data.locations["MISSION_00"].label
    world.set_rule(
        world.get_location(get_mission_event(0)),
        CanReachRegion(world.modified_regions["m005_001a"].HUMAN_NAME),
    )

    world.set_rule(
        get_entrance(world, PInstanceEvent.TANGROWTH.event_name),
        # CanReachRegion(data.regions["m005_001a"].HUMAN_NAME),
        Has(get_mission_event(0)),
    )

    for from_ in [
        "m001_002",
        "m001_003a",
        "m001_004",
        "m001_006",
        "m001_007",
        "m001_008",
        "m001_009",
        "m001_011",
    ]:
        world.set_rule(
            get_connection(world, from_, "m001_003b"),
            # CanReachRegion(data.regions["m005_001a"].HUMAN_NAME),
            Has(get_mission_event(0)),
        )


def set_mission_1_and_2_rules(world: PokemonRSOA):
    mission_1 = data.locations["MISSION_01"].label
    world.set_rule(get_location(world, get_mission_event(1)), Has(get_mission_event(0)))
    world.set_rule(
        get_location(world, mission_1),
        Has(get_mission_event(0)),
    )

    # m005_001b is reached without requiring rules based on
    # the only way to leave school and no obstacles in the way
    # only missions, thus indirect, only need to set this if filtering
    # out even mission 1 and 2.

    """Mission 2 - Investigate the Marine Cave!"""
    """Marine cave"""
    marine_cave = MonSelect.full_map()
    optional_marine = MonSelect.full_map()

    can_destroy_wooden_gate = marine_cave.can_destroy_target(
        "m006_001", 2
    ) | marine_cave.can_destroy_target("m006_001", 3)

    world.set_rule(
        get_connection(world, "m006_001", "m006_002"), can_destroy_wooden_gate
    )
    world.set_rule(
        get_connection(world, "m006_001", "m006_003"),
        can_destroy_wooden_gate & optional_marine.can_destroy_target("m006_001", 1),
    )
    world.set_rule(
        get_pokemon_instance(world, "m006_003", 0),
        optional_marine.can_destroy_target_type(pokemon_to_target_id("graveler")),
    )

    world.set_rule(
        get_location(world, get_instance_target("m006_001", 0)),
        can_destroy_wooden_gate
        & marine_cave.can_destroy_target("m006_001", 0),  # red gigaremo
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

    for i in [5, 6]:
        world.set_rule(
            get_pokemon_instance(world, "m006_002", i),
            optional_marine.can_destroy_target_type(pokemon_to_target_id("geodude")),
        )
    world.set_rule(
        get_connection(world, "m006_002", "m006_004"),
        optional_marine.can_destroy_target("m006_002", 0),  # rock crush 2
    )  # optional when randomized pokémon

    mission_2 = data.locations["MISSION_02"].label
    world.set_rule(
        get_location(world, mission_2), Has(get_instance_target("m006_001", 0))
    )
    world.set_rule(
        get_location(world, get_mission_event(2)),
        Has(get_instance_target("m006_001", 0)),
    )

    for loc in [data.locations["QUEST_01"].label, get_quest_event(1)]:
        world.set_rule(get_location(world, loc), Has(get_mission_event(2)))
    world.set_rule(
        get_entrance(world, PInstanceEvent.MILTANK.event_name),
        Has(get_mission_event(2)),
    )  # not possible if goal is mission 2


def set_mission_3_rules(world: PokemonRSOA):
    all_maps = MonSelect.full_map()

    for loc in [data.locations["QUEST_48"].label, get_quest_event(48)]:
        world.set_rule(get_location(world, loc), Has(get_mission_event(2)))

    """m009_002"""
    # TODO, figure out how mandatory the happiny are and in what way.
    # will affect randomizations.
    world.set_rule(
        get_connection(world, "m004_001", "m009_002"), Has(get_mission_event(2))
    )

    burning_log = all_maps.can_destroy_target_type(72)

    # not at all: 2 cherubi, 4 sphinx, 5 taillow, 8 cherubi, 0xB pichu, 0xC happiny
    for i in [0x13, 0x14]:
        world.set_rule(
            get_pokemon_instance(world, "m009_002", i),
            burning_log,
        )

    for i in [
        0xE,  # happiny
        0xF,  # happiny
        0x10,  # pichu
        0x11,  # sphinx
        0x12,  # wartortle
        # occurences past this require & (target_type(49) | target_type(49))
        # for now irrelevant.
        0x0,  # blastoise
        0x1,  # wartortle
        0x3,  # sphinx
        0x6,  # pichu
        0x7,  # taillow
        0x9,  # cherubi
        0xA,  # cherubi
        0xD,  # wartortle
        0x15,  # beedrill
    ]:
        world.set_rule(
            get_pokemon_instance(world, "m009_002", i),
            burning_log,
        )

    for to in ["m009_001a", "m009_004", "m009_009"]:
        world.set_rule(get_connection(world, "m009_002", to), burning_log)

    for to in ["m009_001b", "m009_001c"]:
        world.set_rule(get_connection(world, "m009_002", to), False_())

    """m009_001a"""

    for to in ["m009_008", "m009_013", "m009_014", "m009_015", "m009_016"]:
        world.set_rule(get_connection(world, "m009_001a", to), False_())

    # wartortle 0x5 is accessible without problems
    for i in [0, 1, 2, 3, 4]:
        world.set_rule(get_pokemon_instance(world, "m009_001a", i), burning_log)

    """m009_009"""
    for i in [2, 3]:
        world.set_rule(get_pokemon_instance(world, "m009_009", i), False_())

    for to in ["m009_001b", "m009_001c"]:
        world.set_rule(get_connection(world, "m009_002", to), False_())

    """m009_004"""

    for i in range(13):
        if i == 8:  # grotle is available through initial connection
            continue
        world.set_rule(
            get_pokemon_instance(world, "m009_004", i),
            False_(),  # requires surf
        )

    for to in ["m009_003", "m009_006"]:
        world.set_rule(get_connection(world, "m009_004", to), False_())

    """Mission 3 complete"""

    for loc in [data.locations["MISSION_03"].label, get_mission_event(3)]:
        world.set_rule(
            get_location(world, loc),
            burning_log
            & all_maps.can_use_field_move(
                FieldMove(category=FieldMoveCategory.RAIN_DANCE, level=1)
            ),
        )


def set_mission_4_rules(world: PokemonRSOA):
    all_maps = MonSelect.full_map()

    """quests"""

    for loc in [data.locations["QUEST_03"].label, get_quest_event(3)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(3)) & Has(data.species[59].event_can_capture),
        )

    without_fallen_tree_section = MonSelect(
        exclude={
            "m009_002": [
                0x3,  # sphinx
                0x6,  # pichu
                0x7,  # taillow
                0x9,  # cherubi
                0xA,  # cherubi
                0xD,  # wartortle
            ]
        }
    )

    for loc in [data.locations["QUEST_11"].label, get_quest_event(11)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(3))
            & without_fallen_tree_section.can_destroy_target("m009_002", 2)
            & without_fallen_tree_section.can_destroy_target("m009_002", 7),
        )  # really identical fallen logs

    for loc in [data.locations["QUEST_49"].label, get_quest_event(49)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(3)) & all_maps.can_destroy_target("m005_001b", 1),
        )

    """m009_001b"""

    for from_ in ["m009_002", "m009_009"]:
        world.set_rule(
            get_connection(world, from_, "m009_001b"), Has(get_mission_event(3))
        )

    for to in ["m009_013", "m009_014", "m009_015", "m009_016"]:
        world.set_rule(get_connection(world, "m009_001b", to), False_())

    """m009_008"""
    for to in ["m009_001c", "m017_001", "m017_002", "m009_011"]:
        world.set_rule(get_connection(world, "m009_008", to), False_())

    # free mons: happiny 00, beedrill 01, pichu 02, beedrill 03,  bonsly 06, beedrill 07, combee 0D,sphinx 0A, buneary 0C, combe 0B
    # bonsly, torterra

    fallen_tree = all_maps.can_destroy_target("m009_008", 1)
    for i in [4, 5]:
        world.set_rule(get_pokemon_instance(world, "m009_008", i), fallen_tree)

    world.set_rule(
        get_pokemon_instance(world, "m009_008", 5),
        fallen_tree
        & all_maps.can_destroy_target_type(pokemon_to_target_id("torterra")),
    )
    world.set_rule(
        get_pokemon_instance(world, "m009_008", 5),
        all_maps.can_destroy_target_type(pokemon_to_target_id("bonsly")),
    )

    # the others are free as well due to side route

    """m009_010"""
    # set to missable as only one is spawned based on chapter scripts
    for to in ["m009_013", "m009_014", "m009_015", "m009_016"]:
        world.set_rule(get_connection(world, "m009_010", to), False_())

    """m009_011"""

    # TODO continue from here

    """m009_001c"""
    # TODO
    for from_ in ["m009_002", "m009_009"]:
        world.set_rule(get_connection(world, from_, "m009_001c"), False_())


def set_completion_condition(world) -> None:
    def captured_n_pokemon(state: CollectionState, n: int) -> bool:
        return (
            sum(
                state.can_reach_location(s.location_capture_name, world.player)
                for s in data.species.values()
            )
            >= n
        )

    # def captured_n_pokemon(state: CollectionState, n: int) -> bool:
    #     return state.has_from_list_unique(
    #         [i.event_add_to_browser for i in data.species.values()], world.player, n
    #     )

    browser = world.options.capture_count_target.value
    browser = 10  # 30
    missions = 1
    quests = 0  # 5

    has_captures = HasFromListUnique(
        *[s.event_add_to_browser for s in data.species.values()], count=browser
    )
    has_missions = True_()
    count = 0
    for loc_name, loc_data in data.locations.items():
        count += 1
        if count > missions:
            break
        if loc_data.category == LocationCategory.MISSION:
            has_missions &= CanReachLocation(loc_data.label)
    has_quests = HasFromListUnique(
        *[get_quest_event(i) for i in range(1, 61)], count=quests
    )
    completion_condition = has_captures & has_missions & has_quests

    world.set_completion_rule(completion_condition)
