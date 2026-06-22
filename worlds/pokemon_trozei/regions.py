from __future__ import annotations


from typing import TYPE_CHECKING, Dict, List, Tuple, Set, Optional

from BaseClasses import Region, Location
from . import data

if TYPE_CHECKING:
    from .world import PokemonTrozei


class PokemonTrozeiLocation(Location):
    game = "PokemonTrozei"


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

    map_1 = Region("Map 1", world.player, world.multiworld)
    regions["Map 1"] = map_1

    region.connect(map_1)

    for i in [0, 5, 1, 2, 6, 7, 30]:
        stage = data.stages[i]
        for name in stage.get_location_names(data.determine_stage_location_count()):
            loc = PokemonTrozeiLocation(
                world.player, name, world.location_name_to_id[name], map_1
            )
            map_1.locations.append(loc)
