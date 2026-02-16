from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Entrance, Region

if TYPE_CHECKING:
    from .world import PokemonRSOA


def create_and_connect_regions(world: PokemonRSOA) -> None:
    create_all_regions(world)
    connect_regions(world)


def create_all_regions(world: PokemonRSOA) -> None:

    overworld = Region("Overworld", world.player, world.multiworld)

    regions = [overworld]

    world.multiworld.regions += regions


def connect_regions(world: PokemonRSOA) -> None:
    overworld = world.get_region("Overworld")

    ...
