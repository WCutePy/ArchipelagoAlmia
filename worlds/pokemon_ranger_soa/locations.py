from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from BaseClasses import ItemClassification, Location

from .data import data

from . import items

if TYPE_CHECKING:
    from .world import PokemonRSOA


class PokemonRSOALocation(Location):
    game = "PokemonRangerSOA"


def location_to_ap_id(location: data.LocationData) -> int:
    raise NotImplementedError
    # return int(location.label)


def create_location_label_to_id_map() -> Dict[str, int]:
    """
    Creates a map from location labels to their AP location id (address)
    """
    label_to_id_map: Dict[str, int] = {}

    # for region_data in data.regions.values():
    #     for location_name in region_data.locations:
    #         location_data = data.locations[location_name]
    #
    #         label_to_id_map[location_data.label] = location_to_ap_id(location_data)

    for browser_id, pokemon in data.species.items():
        location_name = f"Capture {pokemon.name}"
        label_to_id_map[location_name] = browser_id

    return label_to_id_map


def get_location_names_with_ids(location_labels: list[str]) -> dict[str, int | None]:
    location_label_to_id_map = create_location_label_to_id_map()
    return {label: location_label_to_id_map[label] for label in location_labels}


def create_all_locations(world: PokemonRSOA) -> None:
    create_mission_locations(world)
    create_quest_locations(world)
    create_pokemon_locations(world)


def create_mission_locations(world: PokemonRSOA) -> None:
    return


def create_quest_locations(world: PokemonRSOA) -> None:
    return


def create_pokemon_locations(world: PokemonRSOA) -> None:
    # for region_name, region_data in data.regions.items():
    #
    #     region = world.get_region(region_name)

    region = world.get_region("Overworld")

    for browser_id, pokemon in data.species.items():

        if pokemon.browser_id in world.blacklisted_captures:
            continue

        location_name = f"Capture {pokemon.name}"
        new_location = PokemonRSOALocation(
            world.player,
            location_name,
            world.location_name_to_id[location_name],
            region,
        )

        region.locations.append(new_location)
