from __future__ import annotations


from typing import Dict, TYPE_CHECKING, Optional, List, Tuple

from BaseClasses import ItemClassification, CollectionState
from Fill import fill_restrictive
from .data import SpeciesData, data, FieldMove, Party
from .items import PokemonRSOAItem
from .options import RandomizePartners, partner_blacklist, RandomizePokemonEtc

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
    world.modified_regions[map_name].modified = True
    return option


def place_npc(world: PokemonRSOA, place: Tuple[str, int], form_id: int):
    map_name, index = place
    npc = world.modified_regions[map_name].NPCS[index]
    npc.set_form(form_id)
    world.modified_regions[map_name].modified = True


def early_place_random_partners(world: PokemonRSOA) -> None:
    name_to_id = {species.name.lower(): i for i, species in data.species.items()}
    starters = [
        name_to_id[name.lower()] for name in world.options.partner_starters.value
    ]
    partners = [name_to_id[name.lower()] for name in world.options.partners.value]

    all_random = world.options.randomize_partners == RandomizePartners.option_all_random
    starters_only = (
        world.options.randomize_partners == RandomizePartners.option_starter_only
    )

    #  change the blacklist source!!
    allowed_partners = [
        i for i in [*range(1, 267), 435, 436, 437] if i not in partner_blacklist
    ]
    if len(partners) + len(starters) < 18:
        partners += world.random.choices(
            allowed_partners, k=18 - len(partners) - len(starters)
        )
    if len(starters) < 3:
        choices = world.random.sample(partners, k=3 - len(starters))
        for c in choices:
            partners.remove(c)
        starters += choices

    world.random.shuffle(starters)
    world.random.shuffle(partners)

    place_npc(world, ("m005_003", 2), 311)
    place_npc(world, ("m008_006", 5), 311)

    place_npc(world, ("m005_003", 3), 312)
    place_npc(world, ("m008_006", 4), 312)

    place_npc(world, ("m005_003", 4), 313)
    place_npc(world, ("m008_006", 10), 313)

    # apply_place_on_random(world, {"m003_001": [1]}, 311)
    # apply_place_on_random(world, {"m003_001": [2]}, 311)
    # apply_place_on_random(world, {"m003_001": [4]}, 311)

    vanilla_partners_in_some_order = [
        168,  # chimchar
        206,  # piplup
        52,  # turtwig
        213,  # snorunt
        161,  # machop
        80,  # croagunk
        246,  # hippopotas
        164,  # mime jr.
        82,  # kricketot
        84,  # cranidos
        220,  # misdreavus
        251,  # gible
        244,  # sneasel
        181,  # shieldon
    ]
    if starters_only:
        world.modified_partners = starters + vanilla_partners_in_some_order
        return
    world.modified_partners = starters + partners


def early_place_random_restricted(world: PokemonRSOA) -> None:
    """place surf in puel sea"""
    options = {"m011_004": [1, 2, 3]}
    apply_place_on_random(world, options, 0x06A)

    """volcano cave drifloon"""
    options = {
        "m019_003": [1, 3, 4, 5, 6, 7],
        "m019_004": [1, 3, 4, 5, 6, 9],
    }
    apply_place_on_random(world, options, 0x0C4)

    options = {
        "m019_004": [2, 7, 8],
        "m019_016": [0, 1, 2],
    }
    apply_place_on_random(world, options, 0x0C4)


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
        print(world.capture_groups.capture_ocean.locations)
        print(world.capture_groups.capture_ocean.items)
        raise ValueError(
            f"Ocean party: {len(world.capture_groups.capture_ocean)} != {len(world.capture_groups.capture_ocean.items)}"
        )

    party = world.capture_groups.capture

    state_default = CollectionState(world.multiworld)
    state_default.prog_items[world.player]["fill_restrictive"] = 1
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
        state_ocean.prog_items[world.player]["fill_restrictive"] = 1
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
            _, mon_name, mon_id = loc.item.name.split(";")
            mon: SpeciesData = name_to_mon[mon_name]

            region_data = world.modified_regions.get(region_name)
            region_data.modified = True

            species_id = int(mon_id)

            region_data.POKEMON_SPAWN[i].SPECIES_ID = species_id
            region_data.POKEMON_SPAWN[i].SPECIES_NAME = mon_name
    except:
        print("um wat")
        print(loc, mon_name, loc.item)
        raise
    apply_manually_fixed_pokemon(world)
    if world.options.randomize_pokemon_etc != RandomizePokemonEtc.option_vanilla:
        apply_randomize_npc_pokemon(world)


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


def copy_over_spawn_to_npc(
    world: PokemonRSOA, from_map: str, from_i: int, to_map: str, to_i: int
) -> None:
    mon_data = world.modified_regions[from_map].POKEMON_SPAWN[from_i]
    world.modified_regions[to_map].NPCS[to_i].unk2 = mon_data.SPECIES_ID
    world.modified_regions[to_map].NPCS[to_i].NAME = mon_data.SPECIES_NAME


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

    # #  rampardos
    # copy_over_spawn_to_npc(world, "m016_004", 2, "m016_004", 0)
    # copy_over_spawn_to_npc(world, "m016_004", 2, "m016_004", 1)

    return


def apply_randomize_npc_pokemon(world: PokemonRSOA) -> None:
    groups: List[List[Tuple[str, int]]] = [
        [
            ("m201_001", 2),
            ("m201_001", 3),
            ("m201_001", 4),
            ("m201_001", 5),
        ],  # m8 drifloon water
        [("m018_001", i) for i in range(0, 5)],  # m8 drifloon boyleland
        [("m019_013", 0), ("m019_013", 1)],  # m8 drifloon left side
    ]

    pokemon = world.random.choices(list(world.modified_species.keys()), k=len(groups))

    for group, mon in zip(groups, pokemon):
        form_id = list(world.modified_species[mon].forms.keys())[0]
        for place in group:
            place_npc(world, place, form_id)
