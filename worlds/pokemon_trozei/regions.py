from __future__ import annotations


from typing import TYPE_CHECKING, Dict, List, Tuple, Set, Optional

from BaseClasses import Region, Location
from . import data

if TYPE_CHECKING:
    from .world import PokemonTrozei


class PokemonTrozeiLocation(Location):
    game = "Pokemon Trozei"


def create_location_label_to_id_map():
    locations = {}

    index = 0
    for stage in data.stages:
        for name in stage.location_names:
            index += 1
            locations[name] = index
    assert index < 100

    return locations


def create_and_connect_regions(world: PokemonTrozei) -> Dict[str, Region]:
    regions: Dict[str, Region] = {}
    regions[world.origin_region_name] = Region(world.origin_region_name, world.player, world.multiworld)

    create_adventure_region(world, regions)


    return regions


def create_adventure_region(world: PokemonTrozei, regions: Dict[str, Region]) -> None:
    region = Region("Adventure", world.player, world.multiworld)
    regions["Adventure"] = region
    regions[world.origin_region_name].connect(region)

    map_dist = [
        ("Map 1", [
            0, 1, 2, 3,  # laboratory
            5, 6, 7, 12,  # storage
            26,  # huge storage
            30,  # boss
        ]),
        ("Map 2", [
            8, 9, 10, 11, 13, 14,  # storage
            25,  # huge storage
            31, 32  # boss
        ]),
        ("Map 3", [  # top left
            4,  # laboratory
            19, 20, 21,  # storage
            28, 29,  # huge storage
            35,  # boss
        ]),
        ("Map 4", [  # bottom left
            15, 16, 17, 18, 22, 23, 24,  # storage
            27,  # huge storage
            33, 34,  # boss
        ]),
    ]

    for region_name, levels in map_dist:
        region_map = Region(region_name, world.player, world.multiworld)
        regions[region_name] = region_map

        region.connect(region_map, name=region_name)
        for i in levels:
            stage = data.stages[i]
            for name in stage.get_location_names(data.determine_stage_location_count()):
                loc = PokemonTrozeiLocation(
                    world.player, name, world.location_name_to_id[name], region_map
                )
                region_map.locations.append(loc)
