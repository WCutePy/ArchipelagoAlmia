from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Set

from BaseClasses import ItemClassification, Location, Region, LocationProgressType

from .data import data, LocationData, LocationCategory

from . import items
from .items import PokemonRSOAItem

if TYPE_CHECKING:
    from .world import PokemonRSOA


class PokemonRSOALocation(Location):
    game = "PokemonRangerSOA"


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
    default_region = regions.get("Overworld")

    locations_categories = [
        LocationCategory.MISSION,
        LocationCategory.QUEST,
    ]

    for name, location_data in data.locations.items():
        if location_data.category not in locations_categories:
            continue

        if location_data.category in [
            LocationCategory.BROWSER,
            LocationCategory.BROWSER_RANK,
        ]:
            if location_data.name.split("_")[-1] in world.blacklisted_captures:
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

    create_pokemon_locations(world, regions)


def create_quest_locations(world: PokemonRSOA) -> None:
    return


def create_pokemon_locations(
    world: PokemonRSOA,
    regions: Dict[str, Region],
) -> None:
    region = Region("Browser", world.player, world.multiworld)
    regions[region.name] = region
    regions["Overworld"].connect(region, "Browser")

    for browser_id, pokemon in data.species.items():
        location_name = pokemon.location_capture_name
        new_location = PokemonRSOALocation(
            world.player,
            location_name,
            world.location_name_to_id[location_name],
            region,
        )
        region.locations.append(new_location)

        # TODO
        # if pokemon.browser_id in world.blacklisted_captures:
        #     new_location.progress_type = LocationProgressType.EXCLUDED
