from __future__ import annotations

import logging
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
    CanReachEntrance,
    Or,
    And,
)
from .data import (
    data,
    ItemCategory,
    FieldMove,
    LocationCategory,
    pokemon_to_target_id,
    FieldMoveCategory,
    Party,
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

    # print(world.multiworld.regions.)
    full_map = MonSelect.get_rules_scope()

    field_move_rules: Dict[FieldMove, List[Rule]] = {}

    for i in world.capture_groups.get_ids_all:
        pokemon = data.species[i]

        target_id = pokemon_to_target_id(pokemon.name.lower())

        if target_id is None:
            form_rules = []
            for form_id, form in pokemon.forms.items():
                form_rules.append(
                    Has("power_level", count=form.friendship_gauge)
                    & (
                        Has(pokemon.event_add_to_browser(form=form_id))
                        | Has(pokemon.event_can_capture(form=form_id))
                        | Has(
                            pokemon.event_can_capture(party=Party.OCEAN, form=form_id)
                        )
                    )
                )
            base_rule = Or(*form_rules)
        else:
            form_rules = []
            for form_id, form in pokemon.forms.items():
                form_rules.append(
                    Has("power_level", count=form.friendship_gauge)
                    & (
                        Has(pokemon.event_add_to_browser(form=form_id))
                        | (
                            Has(pokemon.event_can_capture(form=form_id))
                            & full_map.can_destroy_target_type(target_id)
                        )
                        | (
                            Has(
                                pokemon.event_can_capture(
                                    party=Party.OCEAN, form=form_id
                                )
                            )
                            & full_map.can_destroy_target_type(target_id, Party.OCEAN)
                        )
                    )
                )
            base_rule = Or(*form_rules)

        world.set_rule(
            get_location(world, pokemon.location_capture_name),
            base_rule,
        )

        start_level = pokemon.field_move.level

        for j in range(1, start_level + 1):
            field_move = FieldMove(category=pokemon.field_move.category, level=j)
            current_rule = field_move_rules.get(field_move, None)
            if current_rule is None:
                field_move_rules[field_move] = [False_(), False_()]

            if target_id is not None:
                normal_destroy = full_map.can_destroy_target_type(target_id)
                ocean_destroy = full_map.can_destroy_target_type(target_id, Party.OCEAN)

                field_move_rules[field_move][0] |= normal_destroy & Or(
                    *[
                        Has("power_level", count=form.friendship_gauge)
                        & Has(pokemon.event_can_capture(form=form_id))
                        for form_id, form in pokemon.forms.items()
                    ]
                )

                field_move_rules[field_move][1] |= ocean_destroy & Or(
                    *[
                        Has("power_level", count=form.friendship_gauge)
                        & Has(pokemon.event_can_capture(Party.OCEAN, form=form_id))
                        for form_id, form in pokemon.forms.items()
                    ]
                )

            else:
                for form_id, form in pokemon.forms.items():
                    field_move_rules[field_move][0] |= Has(
                        "power_level", count=form.friendship_gauge
                    ) & Has(pokemon.event_can_capture(form=form_id))

                    field_move_rules[field_move][1] |= Has(
                        "power_level", count=form.friendship_gauge
                    ) & Has(pokemon.event_can_capture(Party.OCEAN, form=form_id))

    for field_move, pokemon_rules in field_move_rules.items():
        for i, party in enumerate([Party.DEFAULT, Party.OCEAN]):
            field_move_rule = pokemon_rules[i] & has_field_move_item(world, field_move)

            try:
                field_move_location = get_location(
                    world, field_move.event_can_use_field_move_party(party)
                )
                world.set_rule(field_move_location, field_move_rule)
            except KeyError:
                logging.warning(
                    f"{field_move} is part of browser, but potentially not as capture - {party}"
                )

    # for region_name, region_data in world.modified_regions.items():
    #     if not full_map.region_included(region_name, region_data):
    #         continue
    #
    #     for i, mon_data in region_data.POKEMON_SPAWN.items():
    #         if mon_data.SPECIES_NAME in ["Doduo", "Staraptor"]:
    #             world.set_rule(get_pokemon_instance(world, region_name, i), False_())

    set_tutorial_rules(world)
    # set_mission_1_and_2_rules(world)
    # set_mission_3_rules(world)
    # set_mission_4_rules(world)
    goal_based_rules = {
        0: set_tutorial_rules,
        2: set_mission_1_and_2_rules,
        3: set_mission_3_rules,
        4: set_mission_4_rules,
        5: set_mission_5_rules,
        6: set_mission_6_rules,
        7: set_mission_7_rules,
        8: set_mission_8_rules,
    }

    up_to_mission = world.options.mission_clear_target.value
    for i, rule_func in goal_based_rules.items():
        if i <= up_to_mission:
            rule_func(world)

    set_completion_condition(world)

    MonSelect.world = None


def set_tutorial_rules(world: PokemonRSOA) -> None:
    full_map = MonSelect.get_rules_scope()

    world.set_rule(
        get_pokemon_instance(world, "m001_002", 7),
        full_map.can_destroy_target("m001_002", 3),
    )

    # for i in [6, 12]:
    #     world.set_rule(get_pokemon_instance(world, "m001_002", i), False_())
    world.set_rule(get_connection(world, "m001_002", "m001_014"), False_())

    """School first night"""
    has_crate_field_move = has_field_move_item(
        world, data.target_field_move_requirements[27]
    )
    has_gate_field_move = has_field_move_item(
        world, data.target_field_move_requirements[37]
    )

    world.set_rule(
        get_pokemon_instance(world, "m001_004", 0),
        has_crate_field_move,  # crate
    )

    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_007", i),
            has_crate_field_move,  # crate
        )

    world.set_rule(
        get_location(world, PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        has_crate_field_move,  # crate
    )

    # basement access
    for from_ in ["m001_003a", "m001_003b"]:
        world.set_rule(
            get_connection(world, from_, "m001_011"),
            Has(PREvent.SCHOOL_COLLECT_STYLERS.event_name),
        )
    world.set_rule(
        get_location(world, PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        has_crate_field_move & has_gate_field_move,  # crate
    )

    world.set_rule(
        get_pokemon_instance(world, "m001_011", 4),
        has_crate_field_move,  # crate
    )
    for i in [0, 1, 2, 3]:
        world.set_rule(
            get_pokemon_instance(world, "m001_011", i),
            Has(PREvent.SCHOOL_COMPLETE_NIGHT.event_name),
        )

    # world.set_rule(
    #     get_pokemon_instance(world, "m001_011", 5), False_()
    # )  # TODO figure out when separate ghastly spawns

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

    # world.set_rule(
    #     get_connection(world, "m001")
    # )


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
    full_map = MonSelect.get_rules_scope()

    can_destroy_wooden_gate = full_map.can_destroy_target(
        "m006_001", 2
    ) | full_map.can_destroy_target("m006_001", 3)

    world.set_rule(
        get_connection(world, "m006_001", "m006_002"), can_destroy_wooden_gate
    )
    world.set_rule(
        get_connection(world, "m006_001", "m006_003"),
        can_destroy_wooden_gate & full_map.can_destroy_target("m006_001", 1),
    )

    world.set_rule(
        get_location(world, get_instance_target("m006_001", 0)), can_destroy_wooden_gate
    )

    # The pokemon can be added to browser before destroying the machine
    # capturing for field move is only possible after
    for i in range(7):
        world.set_rule(
            get_location(world, get_instance_capture("m006_001", i)),
            full_map.can_destroy_target("m006_001", 0),
        )  # only 2 zubats at first, after mission 2 complete the rest

        if i in [5, 6]:
            continue
        world.set_rule(
            get_pokemon_instance(world, "m006_001", i),
            can_destroy_wooden_gate,
        )

    world.set_rule(
        get_connection(world, "m006_002", "m006_004"),
        full_map.can_destroy_target("m006_002", 0),  # rock crush 2
    )  # optional when randomized pokémon

    mission_2 = data.locations["MISSION_02"].label
    world.set_rule(
        get_location(world, mission_2), full_map.can_destroy_target("m006_001", 0)
    )
    world.set_rule(
        get_location(world, get_mission_event(2)),
        full_map.can_destroy_target("m006_001", 0),
    )


def set_mission_3_rules(world: PokemonRSOA):
    for loc in [data.locations["QUEST_01"].label, get_quest_event(1)]:
        world.set_rule(get_location(world, loc), Has(get_mission_event(2)))
    world.set_rule(
        get_entrance(world, PInstanceEvent.MILTANK.event_name),
        Has(get_mission_event(2)),
    )

    all_maps = MonSelect.get_rules_scope()

    for loc in [data.locations["QUEST_48"].label, get_quest_event(48)]:
        world.set_rule(get_location(world, loc), Has(get_mission_event(2)))

    """m009_002"""
    # TODO, figure out how mandatory the happiny are and in what way.
    # will affect randomizations.
    world.set_rule(
        get_connection(world, "m004_001", "m009_002"), Has(get_mission_event(2))
    )

    burning_log = all_maps.can_destroy_target_type(72)
    completed_mimi = Has(PREvent.GIVE_HAPPINY_TO_MIMI.event_name)

    world.set_rule(
        get_location(world, PREvent.GIVE_HAPPINY_TO_MIMI.event_name),
        Has(data.species[22].event_can_capture(form=211))
        & CanReachLocation(data.species[22].location_capture_name)
        & CanReachRegion(world.modified_regions["m009_002"].HUMAN_NAME),
    )

    # not at all: 2 cherubi, 4 sphinx, 5 taillow, 8 cherubi, 0xB pichu, 0xC happiny
    world.set_rule(
        get_pokemon_instance(world, "m009_002", 0x13),
        all_maps.can_destroy_target_type(72),
    )
    world.set_rule(
        get_pokemon_instance(world, "m009_002", 0x14),
        all_maps.can_destroy_target_type(72) & burning_log,
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

    for to in ["m009_004", "m009_009"]:
        world.set_rule(
            get_connection(world, "m009_002", to), burning_log & completed_mimi
        )

    for to in ["m009_001b", "m009_001c"]:
        world.set_rule(get_connection(world, "m009_002", to), False_())

    """m009_001a"""
    world.set_rule(
        get_connection(world, "m009_001a", "m009_009"), burning_log & completed_mimi
    )

    for to in ["m009_008", "m009_013", "m009_014", "m009_015", "m009_016"]:
        world.set_rule(get_connection(world, "m009_001a", to), False_())

    # wartortle 0x5 is accessible without problems
    for i in [0, 1, 2, 3, 4]:
        world.set_rule(
            get_pokemon_instance(world, "m009_001a", i), burning_log & completed_mimi
        )

    """m009_009"""
    # i 2, 3 are not yet reachable from mission 3

    for to in ["m009_001b", "m009_001c"]:
        world.set_rule(get_connection(world, "m009_002", to), False_())

    """m009_004"""
    # only i 8, grotle is reachable at this stage

    for to in ["m009_003", "m009_006"]:
        world.set_rule(get_connection(world, "m009_004", to), False_())

    """Mission 3 complete"""

    for loc in [data.locations["MISSION_03"].label, get_mission_event(3)]:
        world.set_rule(
            get_location(world, loc),
            burning_log
            & completed_mimi
            & all_maps.can_use_field_move(
                FieldMove(category=FieldMoveCategory.RAIN_DANCE, level=1)
            ),
        )


def set_mission_4_rules(world: PokemonRSOA):
    all_maps = MonSelect.get_rules_scope()

    """quests"""

    for loc in [data.locations["QUEST_03"].label, get_quest_event(3)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(3))
            & Has(data.species[59].event_can_capture())
            & CanReachLocation(data.species[59].location_capture_name),
        )

    """
    During quest 11 te following are unavailable to destroy the first obstacle, 
    but you can cancel the quest to access them again.
    0x3,  # sphinx
    0x6,  # pichu
    0x7,  # taillow
    0x9,  # cherubi
    0xA,  # cherubi
    0xD,  # wartortle
    """

    for loc in [data.locations["QUEST_11"].label, get_quest_event(11)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(3))
            & all_maps.can_destroy_target("m009_002", 2)
            & all_maps.can_destroy_target("m009_002", 7),
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
    for to in ["m009_001c", "m017_001", "m017_002"]:
        world.set_rule(get_connection(world, "m009_008", to), False_())

    # free mons: happiny 00, beedrill 01, pichu 02, beedrill 03,  bonsly 06, beedrill 07, combee 0D,sphinx 0A, buneary 0C, combe 0B
    # bonsly, torterra

    fallen_tree = all_maps.can_destroy_target("m009_008", 1)
    for i in [4, 5]:
        world.set_rule(get_pokemon_instance(world, "m009_008", i), fallen_tree)

    world.set_rule(get_pokemon_instance(world, "m009_008", 5), fallen_tree)

    # the others are free as well due to side route

    """m009_010"""
    # set to missable as only one is spawned based on chapter scripts
    for to in ["m009_013", "m009_014", "m009_015", "m009_016"]:
        world.set_rule(get_connection(world, "m009_010", to), False_())

    """m009_011"""
    # all mons
    for to in ["m009_013", "m009_014", "m009_015", "m009_016"]:
        world.set_rule(get_connection(world, "m009_011", to), False_())

    """m009_012"""
    # staraptor and doduo not catchable yet
    world.set_rule(get_connection(world, "m009_012", "m014_003a"), False_())

    """m009_001c"""
    # TODO
    for from_ in ["m009_002", "m009_009"]:
        world.set_rule(get_connection(world, from_, "m009_001c"), False_())

    """m010"""
    gigaremos_center = all_maps.can_destroy_target(
        "m010_001", 3
    ) & all_maps.can_destroy_target("m010_001", 13)
    west_gate = all_maps.can_destroy_target("m010_022", 11)
    east_gate = all_maps.can_destroy_target("m010_002", 19)

    can_reach_west = gigaremos_center | west_gate | east_gate
    gigaremos_west = (
        all_maps.can_destroy_target("m010_022", 4)
        & all_maps.can_destroy_target("m010_022", 9)
        & can_reach_west
    )

    can_reach_east = gigaremos_west | east_gate
    gigaremos_east = (
        all_maps.can_destroy_target("m010_002", 14)
        & all_maps.can_destroy_target("m010_002", 20)
        & can_reach_east
    )

    if world.options.mission_clear_target.value > 4:
        gigaremos_west |= Has(get_mission_event(4))
        gigaremos_center |= Has(get_mission_event(4))

    """m010_001 center"""
    for i in range(0, 7):
        world.set_rule(
            get_location(world, get_instance_capture("m010_001", i)),
            gigaremos_center | gigaremos_east,
        )

    world.set_rule(
        get_pokemon_instance(world, "m010_001", 6), gigaremos_west | can_reach_east
    )

    world.set_rule(get_connection(world, "m010_001", "m010_022"), can_reach_west)

    for from_, to in [
        ("m010_001", "m014_003b"),
        ("m010_004", "m010_023"),  # leads into DLC
        ("npc_m010_001", "m011_001"),
        ("npc_m010_001", "m201_003"),
    ]:
        world.set_rule(get_connection(world, from_, to), False_())
    """m010_022 west"""

    for i in range(0, 9):
        if i == 6:
            continue
        world.set_rule(
            get_location(world, get_instance_capture("m010_022", i)),
            gigaremos_west | gigaremos_east,
        )
        world.set_rule(get_pokemon_instance(world, "m010_022", i), can_reach_west)
        # I believe one pokemon is missing at the start??? I don't see murkrow at all

        """m010_022 west houses"""
        # These are all fine, and growlithe access is by can reach west on m010_022

    """m010_002 east"""

    for i in range(0, 10):
        if i == 3:
            continue
        world.set_rule(
            get_location(world, get_instance_capture("m010_002", i)), gigaremos_east
        )

        if i == 9:
            continue
        world.set_rule(get_pokemon_instance(world, "m010_002", i), can_reach_east)

    for to in ["m010_006", "m010_007", "m010_013", "m010_014", "m010_015"]:
        world.set_rule(get_connection(world, "m010_002", to), can_reach_east)

    world.set_rule(get_connection(world, "m010_002", "m010_003"), gigaremos_east)

    for to in ["m011_001", "m201_003", "m038_012", "m038_016"]:
        world.set_rule(get_connection(world, "npc_m010_002", to), False_())

        """m010_002 east houses"""
        # elekid possible by access rule
    for from_, to in [
        ("npc_m010_006", "m038_012"),
        ("npc_m010_006", "m038_016"),
        ("npc_m010_015", "m018_001"),
        ("npc_m010_015", "m010_003"),
        ("npc_m010_015", "m201_001"),
    ]:
        world.set_rule(get_connection(world, from_, to), False_())

    """m010_003 port"""

    world.set_rule(
        get_location(world, PREvent.RESCUE_PUELTOWN.event_name),
        gigaremos_east,  # could add needing to defeat toxicroak
    )

    for i in range(
        15,
    ):
        if i in [4, 8, 11]:
            continue
        if i in [14, 13, 12, 10, 9]:
            world.set_rule(
                get_location(world, get_instance_capture("m010_003", i)),
                Has(PREvent.RESCUE_PUELTOWN.event_name),
            )
        else:
            world.set_rule(
                get_pokemon_instance(world, "m010_003", i),
                Has(PREvent.RESCUE_PUELTOWN.event_name),
            )

    for to in ["m011_001", "m201_003"]:
        world.set_rule(get_connection(world, "m010_003", to), False_())

    for to in [
        "m010_003",
        "m018_001",
        "m201_001",
        "m033_001",
        "m201_004",
        "m029_001",
        "m029_007",
    ]:
        world.set_rule(get_connection(world, "npc_m010_003", to), False_())

    """m010_020 Sailors in"""
    for to in [
        "m029_001",
        "m029_007",
        "m201_001",
        "m201_004",
        "m018_001",
        "m033_001",
        "m201_003",
        "m011_001",
    ]:
        world.set_rule(get_connection(world, "npc_m010_020", to), False_())

    """m014_003a"""
    world.set_rule(get_connection(world, "m014_003a", "m014_001"), False_())

    """After saving pueltown"""

    for loc in [data.locations["QUEST_04"].label, get_quest_event(4)]:
        world.set_rule(
            get_location(world, loc),
            Has(PREvent.RESCUE_PUELTOWN.event_name)
            & all_maps.can_destroy_target_type(27),
        )

    for loc in [data.locations["MISSION_04"].label, get_mission_event(4)]:
        world.set_rule(
            get_location(world, loc), Has(PREvent.RESCUE_PUELTOWN.event_name)
        )


def set_mission_5_rules(world: PokemonRSOA):
    all_maps = MonSelect.get_rules_scope()

    for loc in [data.locations["QUEST_02"].label, get_quest_event(2)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(4)) & all_maps.can_destroy_target("m005_001b", 0),
        )

    for loc in [data.locations["QUEST_35"].label, get_quest_event(35)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(4)),
        )

    for event in [
        PInstanceEvent.KRICKETOT,
        PInstanceEvent.CRANIDOS,
        PInstanceEvent.WARTORTLE_WITH_CRANIDOS,
    ]:
        world.set_rule(
            get_entrance(world, event.event_name),
            Has(get_mission_event(4)),
        )

    """m011_001"""
    world.set_rule(
        get_connection(world, "m010_003", "m011_001"),
        Has(get_mission_event(4)),
    )

    world.set_rule(get_connection(world, "m011_001", "m201_002"), False_())
    world.set_rule(get_connection(world, "m011_001", "m201_003"), False_())

    access_north_right = all_maps.can_destroy_target(
        "m011_001",
        0,
    ) | all_maps.can_destroy_target("m011_001", 1)

    world.set_rule(
        get_connection(world, "m011_001", "m011_003"),
        access_north_right,
    )

    for i in [6, 8]:
        world.set_rule(
            get_pokemon_instance(world, "m011_001", i),
            access_north_right,
        )
    """m011_003"""
    access_east_south = all_maps.can_destroy_target("m011_003", 0)
    for i in [9, 10, 11]:
        world.set_rule(
            get_pokemon_instance(world, "m011_003", i),
            access_east_south,
        )

    world.set_rule(
        get_connection(world, "m011_003", "m011_002"),
        access_east_south,
    )

    """m011_002"""
    world.set_rule(
        get_pokemon_instance(world, "m011_002", 8),
        all_maps.can_destroy_target("m011_002", 0)
        | all_maps.can_destroy_target("m011_002", 1),
    )

    access_south_right = access_north_right & access_east_south
    # normal: 1, 8, 3, 0, 5
    for i in [2, 4, 6, 7]:
        world.set_rule(
            get_pokemon_instance(world, "m011_002", i),
            access_south_right,
        )

    world.set_rule(
        get_connection(world, "m011_002", "m011_003"),
        access_south_right,  # maybe change to the inward connection
    )

    swim = FieldMove(category=23, level=1)
    world.set_rule(
        get_connection(
            world,
            "m011_002",
            "m011_004",
        ),
        access_south_right & all_maps.can_use_field_move(swim, party=Party.OCEAN),
    )

    """m011_005"""

    for loc in [data.locations["MISSION_05"].label, get_mission_event(5)]:
        world.set_rule(
            get_location(world, loc),
            # CanReachLocation(get_instance_capture("m011_005", 5)),
            CanReachEntrance(get_pokemon_instance(world, "m011_005", 5).name),
        )


def set_mission_6_rules(world: PokemonRSOA):
    all_maps = MonSelect.get_rules_scope()
    world.set_rule(
        get_connection(world, "m010_001", "m014_003b"),
        Has(get_mission_event(5)),
    )

    for i in [0, 1, 3, 4, 6]:
        world.set_rule(
            get_pokemon_instance(world, "m011_005", i), Has(get_mission_event(5))
        )

    for to in ["m014_004", "m014_005"]:
        world.set_rule(
            get_connection(world, "m014_003b", to),
            False_(),
        )

    """m014_001"""

    world.set_rule(
        get_connection(world, "m014_001", "m021_001"),
        False_(),
    )

    """m014_002"""
    for to in ["m014_004", "m014_005"]:
        world.set_rule(
            get_connection(world, "m014_002", to),
            False_(),
        )

    """m038_001"""
    for to in ["m014_004", "m014_002", "m038_003", "m038_002"]:
        world.set_rule(
            get_connection(world, "m038_001", to),
            False_(),
        )
    world.set_rule(
        get_connection(world, "npc_m038_001", "m038_016"),
        False_(),
    )

    """m014_001 -> m015_001 in logic after story triggers"""
    """m015_001"""
    for to in ["m014_004", "m014_005"]:
        world.set_rule(
            get_connection(world, "m015_001", to),
            False_(),
        )
    for to in ["m015_001", "m016_003"]:
        world.set_rule(
            get_connection(world, "npc_m015_001", to),
            False_(),
        )

    """m015_004"""
    #  TODO not all pokemon here are in logic for it all!!!
    #  make them missable for this rule scope??? (not know cuz eh)
    for to in ["m015_002", "m015_005"]:
        world.set_rule(
            get_connection(world, "m015_004", to),
            False_(),
        )

    world.set_rule(
        get_pokemon_instance(world, "m015_004", 11),
        all_maps.can_destroy_target("m015_004", 0),
    )

    """m017 Ranger Union"""
    world.set_rule(
        get_connection(world, "m017_001", "m017_007"),
        False_(),
    )

    for from_, to in [
        ("m017_002", "m017_004"),
        ("m017_002", "m017_003b"),
        ("npc_m017_002", "m017_008"),
        ("m017_004", "m017_003b"),
        ("npc_m017_004", "m017_005"),
        ("npc_m017_004", "m017_008"),
        ("m017_005", "m017_003b"),
        ("npc_m017_005", "m017_005"),
        ("npc_m017_005", "m017_008"),
        ("m017_006", "m017_003b"),
        ("npc_m017_006", "m017_008"),
        ("m017_007", "m017_003b"),
        ("npc_m017_007", "m017_011"),
        ("npc_m017_007", "m017_007"),
        ("npc_m017_007", "m017_005"),
        ("npc_m017_008", "m017_011"),
        ("npc_m017_008", "m017_005"),
        ("npc_m017_008", "m017_008"),
    ]:
        world.set_rule(
            get_connection(world, from_, to),
            False_(),
        )

    """cutscene"""
    gigaremo_showcase = all_maps.can_destroy_target("m017_004", 0)
    # can do next quests right after before ending the day

    for loc in [data.locations["QUEST_50"].label, get_quest_event(50)]:
        world.set_rule(
            get_location(world, loc),
            gigaremo_showcase,
        )

    world.set_rule(get_pokemon_instance(world, "m010_003", 11), gigaremo_showcase)
    for loc in [data.locations["QUEST_08"].label, get_quest_event(8)]:
        world.set_rule(
            get_location(world, loc),
            gigaremo_showcase
            & (
                Has(data.species[97].event_can_capture(form=69))
                # | Has(data.species[97].event_can_capture(form=281))
            )
            & CanReachLocation(data.species[97].location_capture_name),
        )
    #  TODO fix that it can take either eevee, currently a 69 eevee is forced in specifically.

    world.set_rule(get_pokemon_instance(world, "m011_005", 2), gigaremo_showcase)
    for loc in [data.locations["QUEST_05"].label, get_quest_event(5)]:
        world.set_rule(
            get_location(world, loc),
            gigaremo_showcase
            & CanReachLocation(data.species[87].location_capture_name),
        )
    #  presumbly this is enough, need a bit more testing.

    """m016_001  mission 6"""

    world.set_rule(
        get_connection(world, "m015_004", "m016_001"),
        gigaremo_showcase,
    )

    walk_cliffs = all_maps.can_destroy_target("m016_001", 2) | Has(get_mission_event(6))

    for i in [0, 1, 2]:
        world.set_rule(
            get_pokemon_instance(world, "m016_001", i),
            walk_cliffs,
        )

    """m016_004"""
    #  so this really would best be split up into two regions and the two connections here
    #  if I ever get to changing the way maps are stored in this game.

    world.set_rule(get_connection(world, "m016_004", "m016_002"), walk_cliffs)
    world.set_rule(get_connection(world, "m016_004", "m016_003"), walk_cliffs)

    """m016_003"""
    #  basically can just catch everything by being able to walk the cliffs, even
    #  though the same field move is required one or more times, since these can't simply
    #  be randomized normally

    """m016_004"""

    for i in range(14):
        if i == 2:  # idk where you are
            continue
        world.set_rule(
            get_location(world, get_instance_capture("m016_002", i)),
            all_maps.can_destroy_target("m016_002", 0)
            & all_maps.can_destroy_target("m016_002", 7),
        )

    can_access_mission_complete = all_maps.can_destroy_target(
        "m016_001", 2
    ) | all_maps.can_destroy_target("m016_001", 3)

    world.set_rule(
        get_entrance(world, PInstanceEvent.RAMPARDOS.event_name),
        can_access_mission_complete,
    )
    for loc in [data.locations["MISSION_06"].label, get_mission_event(6)]:
        world.set_rule(
            get_location(world, loc),
            can_access_mission_complete,  # TODO add strength check
        )

    #  TODO fix this (but works for now)
    for i in range(5):
        if i == 2:
            continue
        world.set_rule(
            get_pokemon_instance(world, "m016_004", i), Has(get_mission_event(6))
        )
        #  technically some / multiple can be gotten earlier but idc atm
        #  stil accessible before the *actual* mission complete so included


def set_mission_7_rules(world: PokemonRSOA):
    all_maps = MonSelect.get_rules_scope()

    for i in [0, 1, 4, 5, 6, 8, 9, 10]:
        world.set_rule(
            get_pokemon_instance(world, "m015_004", i),
            Has(get_mission_event(6)),
        )

    for map_name, i in [
        ("m015_001", 0),
        ("m015_001", 1),
        ("m010_003", 15),
        ("m009_012", 0),
    ]:
        world.set_rule(
            get_pokemon_instance(world, map_name, i), Has(get_mission_event(6))
        )

    for loc in [data.locations["QUEST_06"].label, get_quest_event(6)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(6))
            & Has(data.species[44].event_can_capture(form=133))
            & CanReachLocation(data.species[44].location_capture_name),
        )

    world.set_rule(
        get_pokemon_instance(world, "m009_009", 2), Has(get_mission_event(6))
    )
    for loc in [data.locations["QUEST_07"].label, get_quest_event(7)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(6))
            & Has(data.species[109].event_can_capture(form=195))
            & CanReachLocation(data.species[109].location_capture_name),
        )

    for loc in [data.locations["QUEST_09"].label, get_quest_event(9)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(6))
            & Has(data.species[114].event_can_capture(form=22))
            & CanReachLocation(data.species[114].location_capture_name),
        )

    world.set_rule(
        get_entrance(world, PInstanceEvent.TURTWIG.event_name),
        Has(get_mission_event(6)),
    )
    for loc in [data.locations["QUEST_45"].label, get_quest_event(45)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(6))
            & CanReachLocation(data.species[52].location_capture_name),
        )

    world.set_rule(
        get_entrance(world, PInstanceEvent.CROAGUNK.event_name),
        Has(get_mission_event(6)),
    )

    world.set_rule(
        get_pokemon_instance(world, "m001_011", 5), Has(get_mission_event(6))
    )

    world.set_rule(
        get_entrance(world, PInstanceEvent.CARNIVINE_2.event_name),
        Has(get_mission_event(6)),
    )
    for loc in [data.locations["MISSION_07"].label, get_mission_event(7)]:
        world.set_rule(
            get_location(world, loc),
            Has(get_mission_event(6)),  # add strength check?
        )


def set_mission_8_rules(world: PokemonRSOA):
    all_maps = MonSelect.get_rules_scope()
    """Boyleland m018"""
    world.set_rule(
        get_connection(world, "npc_m010_020", "m018_001"), Has(get_mission_event(7))
    )

    for to in ["m201_002", "m010_003", "m033_001"]:
        world.set_rule(get_connection(world, "npc_m018_001", to), False_())

    #  Temporary
    world.set_rule(get_connection(world, "m018_001", "m019_005"), False_())

    #  weird ones
    for from_, to in [("m018_001", "m018_001"), ("npc_m018_005", "m018_005")]:
        world.set_rule(get_connection(world, from_, to), False_())

    """m019_001"""
    #  free access: 1, 6, 7,
    can_airlift = all_maps.can_use_field_move(FieldMove(FieldMoveCategory.AIRLIFT, 1))

    for i in [2, 3, 5]:
        world.set_rule(get_pokemon_instance(world, "m019_001", i), can_airlift)

    #  three unacounted so far!

    world.set_rule(get_connection(world, "m019_001", "m019_003"), can_airlift)
    world.set_rule(get_connection(world, "m019_001", "m019_005"), False_())  # unk

    """m019_003"""
    can_airlift_twice = can_airlift & Has(data.species[142].event_can_capture(), 2)

    for i in range(8):
        if i in [0, 2]:
            continue
        world.set_rule(get_pokemon_instance(world, "m019_003", i), can_airlift_twice)

    world.set_rule(get_connection(world, "m019_003", "m019_004"), can_airlift_twice)

    world.set_rule(get_connection(world, "m019_003", "m019_005"), False_())
    world.set_rule(get_connection(world, "m019_003", "m019_015"), False_())

    """m019_004"""
    #  could add logic based on the event encounters, but eh
    world.set_rule(
        get_connection(world, "m019_004", "m019_010"),
        all_maps.can_destroy_target("m019_004", 4),
    )

    to_crush_2 = all_maps.can_destroy_target("m019_004", 2)
    world.set_rule(get_connection(world, "m019_004", "m019_002"), to_crush_2)
    world.set_rule(get_entrance(world, PInstanceEvent.NUMEL_3.event_name), to_crush_2)

    """m019_002"""
    #  could add defeating the event to get to the ship??
    world.set_rule(get_connection(world, "m019_002", "m020_001"), True_())

    """ship m020_001"""
    world.set_rule(get_connection(world, "m020_001", "m020_016"), False_())

    # world.set_rule(get_connection(world, "m020_001", "m020_002"), False_())
    # world.set_rule(get_connection(world, "m020_001", "m020_005"), False_())


def set_completion_condition(world) -> None:

    # # browser = world.options.capture_count_target.value
    # browser = 180  # 30
    browser = 0
    missions = world.options.mission_clear_target.value
    # missions = 6
    # quests = 16  # 7
    quests = 0

    capture_check = []
    for i in world.capture_groups.get_ids_all:
        mon = data.species[i]
        for form_id in mon.forms.keys():
            capture_check.append(mon.event_add_to_browser(form=form_id))
            capture_check.append(mon.event_can_capture(form=form_id))

    ocean_check = []
    for i in world.capture_groups.get_ids_ocean:
        mon = data.species[i]
        rules = []
        for form_id in mon.forms.keys():
            rules.append(
                Has(
                    mon.event_can_capture(
                        party=Party.OCEAN,
                        form=form_id,
                    )
                )
            )
        ocean_check.append(Or(*rules))

    has_captures = HasFromListUnique(*capture_check, count=browser) & And(*ocean_check)
    has_missions = True_()
    count = 0
    for loc_name, loc_data in data.locations.items():
        count += 1

        if count > missions:
            break
        if loc_data.category == LocationCategory.MISSION:
            has_missions &= Has(get_mission_event(count))

    has_quests = HasFromListUnique(
        *[get_quest_event(i) for i in range(1, 61)], count=quests
    )
    completion_condition = has_captures & has_missions & has_quests
    # completion_condition = Has("EVENT_USE_FIELD-CUT-1")
    # completion_condition = has_captures
    world.set_completion_rule(completion_condition)
