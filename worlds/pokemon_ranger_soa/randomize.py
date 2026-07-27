from __future__ import annotations


from typing import Dict, TYPE_CHECKING, Optional, List, Tuple

from BaseClasses import ItemClassification, CollectionState
from Fill import fill_restrictive
from .data import SpeciesData, data, FieldMove, Party
from .items import PokemonRSOAItem

if TYPE_CHECKING:
    from .world import PokemonRSOA


def apply_place_on_random(
    world: PokemonRSOA, options: Dict[str, List[int]], form_id: int
) -> Tuple[str, int]:
    options = [(key, value) for key, values in options.items() for value in values]
    option = world.random.choice(options)
    map_name, index = option
    spawn = world.modified_regions[map_name].POKEMON_SPAWN[index]
    spawn.set_form(form_id)
    spawn.randomize = False
    return option


def early_place_random_restricted(world: PokemonRSOA) -> None:
    """place surf in puel sea"""
    options = {"m011_004": [1, 2, 3]}
    apply_place_on_random(world, options, 0x06A)


def apply_randomized_pokemon(world: PokemonRSOA) -> None:
    my_progression_items = [
        item
        for item in world.multiworld.itempool
        if item.player == world.player
        and item.classification & ItemClassification.progression
    ]

    if len(world.capture_groups.capture) != len(world.capture_groups.capture.items):
        raise ValueError(
            f"Default party: {len(world.capture_groups.capture)} != {len(world.capture_groups.capture.items)}"
        )

    if len(world.capture_groups.capture_ocean) != len(
        world.capture_groups.capture_ocean.items
    ):
        raise ValueError(
            f"Ocean party: {len(world.capture_groups.capture_ocean)} != {len(world.capture_groups.capture_ocean.items)}"
        )

    party = world.capture_groups.capture

    state_default = CollectionState(world.multiworld)
    for item in my_progression_items:
        state_default.collect(item, True)

    for loc in world.get_locations():
        if "EVENT_USE_FIELD" not in loc.name:
            continue
        if FieldMove.is_party(loc.name) != Party.OCEAN:
            continue
        state_default.collect(loc.item, True)

    fill_restrictive(
        world.multiworld,
        state_default,
        locations=party.locations,
        item_pool=party.items,
        single_player_placement=True,
        swap=True,
        name="Randomize Pokémon - Default",
    )

    party = world.capture_groups.capture_ocean
    if len(party) > 0:
        state_ocean = CollectionState(world.multiworld)
        for item in my_progression_items:
            state_ocean.collect(item, True)
        # for i in range():
        #     for j in range():
        #         try:
        #             state_ocean
        #         except:
        #             pass
        fill_restrictive(
            world.multiworld,
            state_ocean,
            locations=party.locations,
            item_pool=party.items,
            single_player_placement=True,
            swap=True,
            name="Randomize Pokémon - Ocean",
        )

    for loc, item in zip(
        world.capture_groups.missable.locations,
        world.capture_groups.missable.items,
    ):
        loc.item = item

    for cap_loc, browser_loc in world.capture_groups.browser_before_capture:
        cap_loc = world.multiworld.get_location(cap_loc.name, world.player)

        item_name = cap_loc.item.name.replace("CAN_CAPTURE", "ADD_TO_BROWSER")
        assert "ADD_TO_BROWSER" in item_name
        browser_loc.item = PokemonRSOAItem(
            item_name,
            ItemClassification.progression_skip_balancing,
            None,
            world.player,
        )

    name_to_mon: Dict[str, SpeciesData] = {}
    for i, mon in data.species.items():
        name_to_mon[mon.name] = mon
    try:
        for loc in world.multiworld.get_locations(world.player):
            if not (loc.name.startswith("m") and ".P." in loc.name):
                continue
            region_name, _, i = loc.name.split(".")
            i = int(i.strip("_capturebrowsermissableocean"))
            mon_name = loc.item.name.split(";")[1]
            mon: SpeciesData = name_to_mon[mon_name]

            region_data = world.modified_regions.get(region_name)
            region_data.modified = True

            if len(mon.forms) == 1:
                species_id = list(mon.forms.keys())[0]
            else:
                species_id = world.random.choice(list(mon.forms.keys()))

            region_data.POKEMON_SPAWN[i].SPECIES_ID = species_id
            region_data.POKEMON_SPAWN[i].SPECIES_NAME = mon_name
    except:
        print("um wat")
        print(loc, mon_name, loc.item)
        raise
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
