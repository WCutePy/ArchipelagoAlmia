from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple, Set, Optional

from BaseClasses import Entrance, Region, ItemClassification

from .data import (
    data,
    SpeciesData,
    PokemonSpawnEntry,
    FieldMove,
    MapData,
    FieldMoveCategory,
)
from .events import (
    PInstanceEvent,
    PREvent,
    get_instance_target,
    get_instance_base,
    get_instance_browser,
    get_instance_capture,
    get_instance_missable,
)
from .locations import create_event_location
from .options import RandomizePokemon
from .MonSelect import MonSelect

if TYPE_CHECKING:
    from .world import PokemonRSOA


def attach_pokemon_encounter(
    world: PokemonRSOA,
    species: SpeciesData,
    instance_name: str,
    spawn_data: PokemonSpawnEntry,
    connect_to: Region,
) -> Region:
    pokemon_region = Region(instance_name, world.player, world.multiworld)
    connect_to.connect(pokemon_region, instance_name)

    place_locked = False
    if (
        world.options.randomize_pokemon == RandomizePokemon.option_vanilla
        or not spawn_data.randomize
    ):
        place_locked = True

    if spawn_data.missable:
        browser_name = get_instance_missable(instance_name)
        item_name = species.event_missable
    elif spawn_data.one_time:
        browser_name = get_instance_browser(instance_name)
        item_name = species.event_add_to_browser
    else:
        browser_name = get_instance_capture(instance_name)
        item_name = species.event_can_capture
    loc = create_event_location(
        world,
        browser_name,
        pokemon_region,
        event_item_name=item_name,
        place_locked=place_locked,
    )

    if spawn_data.browser_before_capture:
        browser_name = get_instance_browser(instance_name)
        item_name = species.event_add_to_browser
        browser_loc = create_event_location(
            world, browser_name,
            pokemon_region,
            event_item_name=item_name,
            place_locked=place_locked
        )
        world.browser_before_capture.append(browser_loc)

    if place_locked:
        return pokemon_region

    if spawn_data.missable:
        world.missable_captures.append(loc)
    elif spawn_data.one_time:
        world.browser_captures.append(loc)
    else:
        world.capture_captures.append(loc)

    return pokemon_region


def create_and_connect_regions(world: PokemonRSOA) -> Dict[str, Region]:
    regions: Dict[str, Region] = {}

    form_species: Dict[int, SpeciesData] = {}
    for browser_i, species_data in data.species.items():
        for i in species_data.form_ids:
            form_species[i] = species_data

    connections: List[Tuple[str, str, str]] = []

    """Logic chain"""
    MonSelect.world = world
    full_map = MonSelect.get_rules_scope()
    browser_before_captures = MonSelect.browser_before_capture()

    for region_name, region_data in world.modified_regions.items():

        new_region = Region(region_data.HUMAN_NAME, world.player, world.multiworld)

        regions[region_name] = new_region

        for exit_name in region_data.EXITS:
            region_exit = exit_name.split("-> ")[1].split(".")[0]
            connections.append((exit_name, region_name, region_exit))

        if not full_map.region_included(region_name, region_data):
            continue

        for i, target_data in region_data.TARGETS.items():
            field_move = data.target_field_move_requirements[target_data.TARGET_ID]
            if field_move.category == FieldMoveCategory.NONE:
                continue

            event_name = get_instance_target(region_name, i)

            target_location = create_event_location(world, event_name, new_region)

        for i, spawn_data in region_data.POKEMON_SPAWN.items():
            if not full_map.instance_included(region_name, i):
                continue
            if browser_before_captures.instance_included(region_name, i):
                spawn_data.browser_before_capture = True
            pokemon_instance = get_instance_base(region_name, i)
            species = data.form_id_to_species[spawn_data.SPECIES_ID]

            p_region = attach_pokemon_encounter(
                world, species, pokemon_instance, spawn_data, new_region
            )
            regions[pokemon_instance] = p_region

    for name, source, dest in connections:
        source = regions.get(source, None)
        dest = regions.get(dest, None)
        if source is None or dest is None:
            continue
        source.connect(dest, name)

    regions["Overworld"] = Region("Overworld", world.player, world.multiworld)
    regions["Overworld"].connect(regions["m001_013"], "Start Game")

    """Additional connections that behave different"""

    regions["m029_001"].connect(
        regions["m030_001"], "Oil Field Hideout"
    )  # TODO, connect to proper region
    regions["m029_001"].connect(regions["m029_009"], "Wailord fight")

    for event in PInstanceEvent.events():
        if event not in full_map.event_mon:
            continue

        pokemon = data.species[event.browser_id]

        p_region = attach_pokemon_encounter(
            world,
            pokemon,
            event.event_name,
            PokemonSpawnEntry(
                SPECIES_ID=pokemon.form_ids[0],
                SPECIES_NAME=pokemon.name,
                SPAWN_FLAG=-1,
                one_time=event.one_time,
                randomize=False,
            ),
            regions[event.map_name],
        )
        regions[event.event_name] = p_region

    field_move_region = regions["Overworld"]

    regions["Events"] = Region("Events", world.player, world.multiworld)
    regions["Overworld"].connect(regions["Events"], "Events region")
    for event in PREvent:
        create_event_location(world, event.event_name, regions["Events"])

    return regions
