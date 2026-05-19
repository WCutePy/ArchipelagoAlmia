from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple, Set

from BaseClasses import Entrance, Region, ItemClassification
from rule_builder.rules import Has, Rule

from .data import data, SpeciesData, FieldMoveCategory, PokemonSpawnEntry, FieldMove
from .items import PokemonRSOAItem
from .locations import PokemonRSOALocation
from .events import PInstanceEvent

if TYPE_CHECKING:
    from .world import PokemonRSOA


def create_event_location(
    world: PokemonRSOA, event_name: str, event_region: Region
) -> PokemonRSOALocation:
    event_location = PokemonRSOALocation(world.player, event_name, None, event_region)
    event_location.show_in_spoiler = False

    event_location.place_locked_item(
        PokemonRSOAItem(
            event_name,
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )
    )
    event_region.locations.append(event_location)
    return event_location


def attach_pokemon_encounter(
    world: PokemonRSOA,
    instance_name: str,
    spawn_data: PokemonSpawnEntry,
    connect_to: Region,
) -> None:
    pokemon_region = Region(instance_name, world.player, world.multiworld)

    create_event_location(world, f"{instance_name}_browser", pokemon_region)

    if not spawn_data.one_time:
        create_event_location(world, f"{instance_name}_capture", pokemon_region)

    connect_to.connect(pokemon_region, instance_name)


def create_and_connect_regions(world: PokemonRSOA) -> Dict[str, Region]:
    regions: Dict[str, Region] = {}

    form_species: Dict[int, SpeciesData] = {}
    for browser_i, species_data in data.species.items():
        for i in species_data.form_ids:
            form_species[i] = species_data

    connections: List[Tuple[str, str, str]] = []
    for region_name, region_data in data.regions.items():

        if any(
            w in region_data.HUMAN_NAME
            for w in [
                "DLC",
                "-UNK",
                "-UNUSED",
                "ALTRU_TOWER-SKY-BLUE",
                "ALTRU_TOWER-6F_ROOF-DARK_CRYSTAL_DARK_CLOUDS_2",
                "VIENTOWN-RANGER_STATION_BACKROOM",
                "OIL_FIELD_HIDEOUT-B2_WEST_HALLWAY-DARK",
            ]
        ):
            continue

        new_region = Region(region_data.HUMAN_NAME, world.player, world.multiworld)

        for i, target_data in region_data.TARGETS.items():
            event_name = f"{region_name}.T.{i}"
            target_location = create_event_location(world, event_name, new_region)

            field_move = data.target_field_move_requirements[target_data.TARGET_ID]
            if field_move.category != FieldMoveCategory.NONE:
                world.set_rule(
                    target_location, Has(field_move.event_can_use_field_move)
                )

        for i, spawn_data in region_data.POKEMON_SPAWN.items():
            pokemon_instance = f"{region_name}.P.{i}"

            attach_pokemon_encounter(world, pokemon_instance, spawn_data, new_region)

        for exit_name in region_data.EXITS:
            region_exit = exit_name.split("-> ")[1].split(".")[0]
            connections.append((exit_name, region_name, region_exit))

        regions[region_name] = new_region

    for name, source, dest in connections:
        source = regions.get(source, None)
        dest = regions.get(dest, None)
        if source is None or dest is None:
            continue
        source.connect(dest, name)

    regions["Overworld"] = Region("Overworld", world.player, world.multiworld)
    regions["Overworld"].connect(regions["m001_013"], "Start Game")

    """Additional connections that behave different"""

    regions["Overworld"].connect(
        regions["m030_001"], "Oil Field Hideout"
    )  # TODO, connect to proper region
    regions["m029_001"].connect(regions["m029_009"], "Wailord fight")

    for event in PInstanceEvent:
        pokemon = data.species[event.browser_id]

        attach_pokemon_encounter(
            world,
            event.event_name,
            PokemonSpawnEntry(
                SPECIES_ID=pokemon.form_ids[0],
                SPECIES_NAME=pokemon.name,
                SPAWN_FLAG=-1,
                one_time=event.one_time,
            ),
            regions[event.map_name],
        )

    field_move_region = regions["Overworld"]
    field_moves: Set[FieldMove] = set()

    for i, pokemon in data.species.items():
        field_moves.add(pokemon.field_move)

    for field_move in field_moves:
        create_event_location(
            world, field_move.event_can_use_field_move, field_move_region
        )

    return regions
