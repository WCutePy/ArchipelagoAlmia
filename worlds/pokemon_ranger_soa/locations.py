from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Set, Optional

from BaseClasses import ItemClassification, Location, Region, LocationProgressType

from .data import data, LocationData, LocationCategory, SpeciesData, FieldMove, Party
from .events import PInstanceEvent
from .items import PokemonRSOAItem
from .options import RandomizePokemonEncounters
from .MonSelect import MonSelect

if TYPE_CHECKING:
    from .world import PokemonRSOA


class PokemonRSOALocation(Location):
    game = "PokemonRangerSOA"


def create_event_location(
    world: PokemonRSOA,
    event_loc_name: str,
    event_region: Region,
    event_item_name: Optional[str] = None,
    show_spoiler: bool = True,  # todo swithc
    place_locked: bool = True,
) -> PokemonRSOALocation:
    if event_item_name is None:
        event_item_name = event_loc_name
    event_location = PokemonRSOALocation(
        world.player, event_loc_name, None, event_region
    )
    event_region.locations.append(event_location)

    if not show_spoiler:
        event_location.show_in_spoiler = False

    if not place_locked:
        return event_location

    event_location.place_locked_item(
        PokemonRSOAItem(
            event_item_name,
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )
    )
    return event_location


def location_to_ap_id(location: data.LocationData) -> int:
    return location.id


def ap_id_to_location(id) -> data.LocationData:
    return next(location for location in data.locations.values() if location.id == id)


def create_location_label_to_id_map() -> Dict[str, int]:
    """
    Creates a map from location labels to their AP location id (address)
    """
    label_to_id_map: Dict[str, int] = {}

    for name, location_data in data.locations.items():
        label_to_id_map[location_data.label] = location_to_ap_id(location_data)

    return label_to_id_map


def get_location_names_with_ids(location_labels: list[str]) -> dict[str, int | None]:
    location_label_to_id_map = create_location_label_to_id_map()
    return {label: location_label_to_id_map[label] for label in location_labels}


def create_all_locations(
    world: PokemonRSOA,
    regions: Dict[str, Region],
) -> None:

    create_pokemon_locations(world, regions)

    default_region = regions.get("Overworld")

    locations_categories = [
        LocationCategory.MISSION,
        LocationCategory.QUEST,
    ]

    max_mission = world.options.mission_clear_target.value
    permitted_quests = []
    quests_table = {
        3: [1, 48],
        4: [3, 11, 49, 4],
        5: [2, 35],
        6: [5, 8, 50],
        7: [6, 7, 9, 45],
    }
    for i in range(0, max_mission + 1):
        permitted_quests += quests_table.get(i, [])

    for name, location_data in data.locations.items():
        if location_data.category not in locations_categories:
            continue

        if location_data.category == LocationCategory.MISSION:
            if int(name.strip("MISSION_")) > max_mission:
                continue
        elif location_data.category == LocationCategory.QUEST:
            if int(name.strip("QUEST_")) not in permitted_quests:
                continue

        if location_data.parent_region is None:
            region = default_region
        else:
            region = regions[location_data.parent_region]

        new_location = PokemonRSOALocation(
            world.player,
            location_data.label,
            world.location_name_to_id[location_data.label],
            region,
        )

        region.locations.append(new_location)

        if location_data.category in [LocationCategory.MISSION, LocationCategory.QUEST]:
            create_event_location(world, f"COMPLETE_{name}", region, show_spoiler=True)


def create_quest_locations(world: PokemonRSOA) -> None:
    return


def create_pokemon_locations(
    world: PokemonRSOA,
    regions: Dict[str, Region],
) -> None:

    region = Region("Browser", world.player, world.multiworld)
    regions[region.name] = region
    regions["Overworld"].connect(region, "Browser")

    full_map = MonSelect.get_rules_scope()
    if world.options.randomize_pokemon == RandomizePokemonEncounters.option_vanilla:

        for pokemon_id in world.capture_groups.get_ids_all:
            pokemon = data.species[pokemon_id]
            location_name = pokemon.location_capture_name
            new_location = PokemonRSOALocation(
                world.player,
                location_name,
                world.location_name_to_id[location_name],
                region,
            )
            region.locations.append(new_location)

        field_move_region = regions["Overworld"]
        add_field_move_events(
            world, world.capture_groups.get_ids_default, field_move_region
        )
        add_field_move_events(
            world, world.capture_groups.get_ids_ocean, field_move_region
        )
        return

    missable_mons = len(world.capture_groups.missable)
    browser_mons = len(world.capture_groups.browser)
    capture_mons = len(world.capture_groups.capture)
    capture_ocean_mons = len(world.capture_groups.capture_ocean)

    available_pool = [
        i
        for i in [*range(1, 267), 435, 436, 437]
        if i not in world.blacklisted_captures
    ]

    one_count = min(len(available_pool), capture_mons)
    one_each = world.random.sample(available_pool, one_count)

    normal_include = [
        17,
        4,
        14,
        13,
        22,
        59,  # combee quest
        [97, 69],  # eevee quest
        114,  # oddish quest
        109,  # ambipom
        44,  # nosepass
        142,  # drifloon
        142,  # drifloon numba 2!
    ]

    ocean_captures = [
        86,  # finneon for crush 1
        207,  # prinplup for cut 2
        91,  # mantine to swim
    ]

    add_to = world.random.choices([0, 1], weights=[capture_mons, capture_ocean_mons])[0]
    [normal_include, ocean_captures][add_to].append(
        87,  # lumineon
    )

    for i in normal_include:  # TODO, don't do this like this. # HARDCODED BROWSER IDS
        one_each.pop(0)
        one_each.append(i)

    dupe_captures = world.random.choices(available_pool, k=capture_mons - one_count)
    captures = one_each + dupe_captures

    if capture_ocean_mons == 0:
        ocean_captures.clear()
    ocean_captures += world.random.choices(
        available_pool, k=capture_ocean_mons - len(ocean_captures)
    )

    for i in captures:
        if isinstance(i, list):
            i, form = i
            mon = data.species[i]
        else:
            mon = data.species[i]
            choices = list(mon.forms.keys())
            if len(choices) == 1:
                form = choices[0]
            else:
                form = world.random.choice(choices)

        new_item = PokemonRSOAItem(
            mon.event_can_capture(form=form),
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )
        world.capture_groups.capture.append(new_item)
        world.capture_groups.default_ids_used.add(i)

    for i in ocean_captures:
        mon = data.species[i]
        choices = list(mon.forms.keys())
        if len(choices) == 1:
            form = choices[0]
        else:
            form = world.random.choice(choices)
        new_item = PokemonRSOAItem(
            mon.event_can_capture(Party.OCEAN, form=form),
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )
        world.capture_groups.capture_ocean.append(new_item)
        world.capture_groups.ocean_ids_used.add(i)

    # TODO ensure all necessary field moves are inside the capture list *first*

    for i in world.capture_groups.get_ids_all:
        mon = data.species[i]

        location_name = mon.location_capture_name
        new_location = PokemonRSOALocation(
            world.player,
            location_name,
            world.location_name_to_id[location_name],
            region,
        )
        region.locations.append(new_location)

    field_move_region = regions["Overworld"]
    add_field_move_events(
        world,
        world.capture_groups.get_ids_default,
        field_move_region,
        party=Party.DEFAULT,
    )
    add_field_move_events(
        world, world.capture_groups.get_ids_ocean, field_move_region, party=Party.OCEAN
    )

    missable_options = [
        i
        for i in world.capture_groups.get_ids_all
        if i not in world.blacklisted_captures
    ]
    missable_items = world.random.choices(missable_options, k=missable_mons)
    for i in missable_items:
        mon = data.species[i]
        choices = list(mon.forms.keys())
        if len(choices) == 1:
            form = choices[0]
        else:
            form = world.random.choice(choices)
        new_item = PokemonRSOAItem(
            mon.event_missable(form=form),
            ItemClassification.filler,
            None,
            world.player,
        )
        world.capture_groups.missable.append(new_item)


def add_field_move_events(world, pool, region, party: Party = Party.DEFAULT):
    field_moves: Set[FieldMove] = set()

    for i in pool:
        pokemon = data.species[i]
        start_level = pokemon.field_move.level

        for j in range(1, start_level + 1):
            field_move = FieldMove(category=pokemon.field_move.category, level=j)
            field_moves.add(field_move)

    field_moves = sorted(field_moves)
    for field_move in field_moves:
        create_event_location(
            world, field_move.event_can_use_field_move_party(party), region
        )
