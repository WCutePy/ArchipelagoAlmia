from __future__ import annotations


from typing import Dict, TYPE_CHECKING, Optional

from BaseClasses import ItemClassification, CollectionState
from Fill import fill_restrictive
from .data import SpeciesData, data
from .items import PokemonRSOAItem

if TYPE_CHECKING:
    from .world import PokemonRSOA


def apply_randomized_pokemon(world: PokemonRSOA) -> None:
    my_progression_items = [
        item
        for item in world.multiworld.itempool
        if item.player == world.player
        and item.classification & ItemClassification.progression
    ]

    state = CollectionState(world.multiworld)
    for item in my_progression_items:
        state.collect(item, True)

    if len(world.to_fill_capture_groups.capture) != len(
        world.to_fill_capture_groups.capture.items
    ):
        raise ValueError(
            f"{len(world.to_fill_capture_groups.capture)} != {len(world.to_fill_capture_groups.capture.items)}"
        )

    fill_restrictive(
        world.multiworld,
        state,
        locations=world.to_fill_capture_groups.capture.locations,
        item_pool=world.to_fill_capture_groups.capture.items,
        single_player_placement=True,
        swap=True,
        name="Randomize Pokémon",
    )

    for loc, item in zip(
        world.to_fill_capture_groups.missable.locations,
        world.to_fill_capture_groups.missable.items,
    ):
        loc.item = item

    print("these are the important")
    for loc in world.browser_before_capture:
        cap_loc_name = loc.name.replace("browser", "capture")
        print(loc, cap_loc_name)
        cap_loc = world.multiworld.get_location(cap_loc_name, world.player)
        item_name = cap_loc.item.name.replace("CAN_CAPTURE", "ADD_TO_BROWSER")
        assert "ADD_TO_BROWSER" in item_name
        loc.item = PokemonRSOAItem(
            item_name,
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )

    name_to_mon: Dict[str, SpeciesData] = {}
    for i, mon in data.species.items():
        name_to_mon[mon.name] = mon
    for loc in world.multiworld.get_locations(world.player):
        if not (loc.name.startswith("m") and ".P." in loc.name):
            continue
        region_name, _, i = loc.name.split(".")
        i = int(i.strip("_capturebrowsermissable"))
        mon_name = loc.item.name.split(";")[1]
        mon: SpeciesData = name_to_mon[mon_name]

        region_data = world.modified_regions.get(region_name)
        region_data.modified = True

        if len(mon.form_ids) == 1:
            species_id = mon.form_ids[0]
        else:
            species_id = world.random.choice(mon.form_ids)

        region_data.POKEMON_SPAWN[i].SPECIES_ID = species_id
        region_data.POKEMON_SPAWN[i].SPECIES_NAME = mon_name

    apply_manually_fixed_pokemon(world)


def copy_over_map_pokemon(
    world: PokemonRSOA, from_: str, to: str, mapping: Optional[Dict[int, int]]
) -> None:
    from_map = world.modified_regions[from_]
    to_map = world.modified_regions[to]
    if not mapping and len(from_map.POKEMON_SPAWN.keys()) != len(
        to_map.POKEMON_SPAWN.keys()
    ):
        raise ValueError(
            f"Two unequally sized maps have been passed without a mapping table: {from_=}, {to=}"
        )

    to_map.modified = True
    for i, mon_data in from_map.POKEMON_SPAWN.items():

        if mapping:
            j = mapping.get(i, None)
            if j is None:
                continue
        else:
            j = i
        to_map.POKEMON_SPAWN[j].SPECIES_ID = mon_data.SPECIES_ID
        to_map.POKEMON_SPAWN[j].SPECIES_NAME = mon_data.SPECIES_NAME


def apply_manually_fixed_pokemon(world: PokemonRSOA) -> None:

    m009_001a_to_m009_001b = {
        0: 0,
        1: 1,
        2: 7,
        3: 5,
        4: 6,
        5: 9,
    }
    copy_over_map_pokemon(world, "m009_001a", "m009_001b", m009_001a_to_m009_001b)

    return
