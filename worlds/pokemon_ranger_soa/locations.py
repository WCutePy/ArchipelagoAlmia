from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Set, Optional

from BaseClasses import ItemClassification, Location, Region, LocationProgressType

from .data import data, LocationData, LocationCategory, SpeciesData, FieldMove
from .events import PInstanceEvent
from .items import PokemonRSOAItem
from .options import RandomizePokemon
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
    quests_table = {3: [1, 48], 4: [3, 11, 49, 4]}
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
    if world.options.randomize_pokemon == RandomizePokemon.option_vanilla:
        possible_captures = set()

        for region_name, region_data in world.modified_regions.items():
            if not full_map.region_included(region_name, region_data):
                continue
            for i, mon_data in region_data.POKEMON_SPAWN.items():
                if not full_map.instance_included(region_name, i):
                    continue

                if mon_data.missable:
                    continue
                pokemon = data.form_id_to_species[mon_data.SPECIES_ID]
                if not mon_data.one_time:
                    possible_captures.add(pokemon.browser_id)

                if pokemon.browser_id in world.included_browser_entries:
                    continue
                """Does currently not support blacklisting"""
                location_name = pokemon.location_capture_name
                new_location = PokemonRSOALocation(
                    world.player,
                    location_name,
                    world.location_name_to_id[location_name],
                    region,
                )
                region.locations.append(new_location)

                world.included_browser_entries.add(pokemon.browser_id)

        field_move_region = regions["Overworld"]
        add_field_move_events(world, possible_captures, field_move_region)
        return

    missable_mons = 0
    browser_mons = 0
    capture_mons = 0
    already_used_ids: Set[int] = set()
    for loc in world.get_locations():
        if ".P." not in loc.name and "_P_" not in loc.name:
            continue

        if loc.locked:
            if "EVENT_P_" in loc.name:
                name = "_".join(loc.name.split("_")[2:-1])
                value: PInstanceEvent = getattr(PInstanceEvent, name)
                already_used_ids.add(value.browser_id)

            elif loc.item is not None and "EVENT" in loc.item.name:
                if "missable" in loc.item.name.lower():
                    continue
                m, _, i = loc.name.split(".")
                i = i.lower().strip("_capturebowsmisbl")
                b_id = data.form_id_to_species[
                    world.modified_regions[m].POKEMON_SPAWN[int(i)].SPECIES_ID
                ].browser_id
                already_used_ids.add(b_id)

            continue

        if "missable" in loc.name:
            missable_mons += 1

        if "browser" in loc.name:
            browser_mons += 1

        if "capture" in loc.name:
            capture_mons += 1

    print(browser_mons, capture_mons, already_used_ids)
    # for event_loc in event_mons:     # TODO, but none are editable right now

    available_pool = [
        i
        for i in [*range(1, 267), 435, 436, 437]
        if i not in world.blacklisted_captures
    ]

    one_count = min(len(available_pool), capture_mons)
    one_each = world.random.sample(available_pool, one_count)

    for i in [
        17,
        4,
        14,
        13,
        22,
        59  # combee quest
    ]:  # TODO, don't do this like this. # HARDCODED BROWSER IDS
        one_each.pop(0)
        one_each.append(i)

    dupe_captures = world.random.choices(available_pool, k=capture_mons - one_count)
    captures = one_each + dupe_captures

    for i in captures:
        mon = data.species[i]
        new_item = PokemonRSOAItem(
            mon.event_can_capture,
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )
        world.capture_items.append(new_item)
        already_used_ids.add(i)

    # TODO ensure all necessary field moves are inside the capture list *first*

    for i in already_used_ids:
        mon = data.species[i]

        location_name = mon.location_capture_name
        new_location = PokemonRSOALocation(
            world.player,
            location_name,
            world.location_name_to_id[location_name],
            region,
        )
        region.locations.append(new_location)
    world.included_browser_entries |= already_used_ids

    field_move_region = regions["Overworld"]
    add_field_move_events(world, one_each, field_move_region)

    missable_items = world.random.choices(
        list(world.included_browser_entries), k=missable_mons
    )
    for i in missable_items:
        mon = data.species[i]
        new_item = PokemonRSOAItem(
            mon.event_missable,
            ItemClassification.filler,
            None,
            world.player,
        )
        world.missable_items.append(new_item)


def add_field_move_events(world, pool, region):
    field_moves: Set[FieldMove] = set()

    for i in pool:
        pokemon = data.species[i]
        start_level = pokemon.field_move.level

        for j in range(1, start_level + 1):
            field_move = FieldMove(category=pokemon.field_move.category, level=j)
            field_moves.add(field_move)

    field_moves = sorted(field_moves)
    for field_move in field_moves:
        create_event_location(world, field_move.event_can_use_field_move, region)
