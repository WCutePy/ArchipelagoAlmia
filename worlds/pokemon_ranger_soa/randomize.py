from __future__ import annotations


from typing import Dict, TYPE_CHECKING, Optional, List, Tuple

from BaseClasses import ItemClassification, CollectionState
from Fill import fill_restrictive
from .data import SpeciesData, data, FieldMove, Party, FieldMoveCategory
from .items import PokemonRSOAItem
from .options import RandomizePartners, partner_blacklist, RandomizePokemonEtc

if TYPE_CHECKING:
    from .world import PokemonRSOA


def apply_place_on_random(
    world: PokemonRSOA, options: Dict[str, List[int]], form_id: int
) -> Tuple[str, int]:
    options = [(key, value) for key, values in options.items() for value in values]
    if len(options) == 1:
        option = options[0]
    else:
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


def form_options_by_criteria(
    world: PokemonRSOA, field_move: FieldMove, health: int, exact: bool = True
):
    options = []
    lowest_form = None
    lowest_health: int | None = None

    for species in world.modified_species.values():
        if field_move.category != species.field_move.category:
            continue
        if exact and field_move.level != species.field_move.level:
            continue
        elif not exact and species.field_move.level < field_move.level:
            continue
        for form, form_data in species.forms.items():
            if lowest_form is None or lowest_health > form_data.friendship_gauge:
                lowest_form = form
                lowest_health = form_data.friendship_gauge
            if form_data.friendship_gauge > health:
                continue
            options.append(form)

    if options:
        return options
    return [lowest_form]


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

    vanilla_partners_in_some_order = [
        82,  # kricketot
        84,  # cranidos
        80,  # croagunk
        164,  # mime jr.
        181,  # shieldon
        #
        168,  # chimchar
        206,  # piplup
        52,  # turtwig
        213,  # snorunt
        161,  # machop
        246,  # hippopotas
        220,  # misdreavus
        251,  # gible
        244,  # sneasel
    ]
    if starters_only:
        world.modified_partners = starters + vanilla_partners_in_some_order
        return
    # kricketot
    place_npc(world, ("m008_006", 8), 314)
    place_npc(world, ("m008_006", 12), 314)

    # cranidos
    place_npc(world, ("m008_006", 9), 315)
    place_npc(world, ("m016_003", 1), 315)

    # turtwig
    place_npc(world, ("m008_008", 0), 316)
    place_npc(world, ("m004_007", 0), 316)

    # croagunk
    place_npc(world, ("m008_008", 2), 317)
    place_npc(world, ("m002_001", 9), 317)

    # mime jr
    place_npc(world, ("m008_008", 4), 318)
    place_npc(world, ("m001_014", 7), 318)
    # place_npc(world, ("m018_001", 21), 318) unsure if this is the partner mime jr or not!!!
    place_npc(world, ("m019_002", 15), 318)
    place_npc(world, ("m020_002", 0), 318)
    place_npc(world, ("m020_005", 1), 318)
    place_npc(world, ("m020_009", 7), 318)
    place_npc(world, ("m020_014", 0), 318)
    place_npc(world, ("m020_016", 1), 318)

    # shieldon
    place_npc(world, ("m008_006", 9), 319)
    place_npc(world, ("m016_003", 1), 319)

    ...

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

    """place the whole ship required section"""
    max_health = 2000
    recharge_options_1 = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.RECHARGE, level=1), max_health
    )
    recharge_options_2 = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.RECHARGE, level=2), max_health
    )
    form_options = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.ELECTRIFY, level=2), max_health
    )
    options = {
        "m020_001": [0, 1, 2, 3, 4, 5, 6],  # all
        "m020_002": [*range(0, 13)],  # all
        # m020_016 when those ralts??
    }
    out = apply_place_on_random(world, options, world.random.choice(form_options))
    options[out[0]].remove(out[1])
    form_options = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.CRUSH, level=2), max_health
    )
    out = apply_place_on_random(world, options, world.random.choice(form_options))
    options[out[0]].remove(out[1])
    out = apply_place_on_random(world, options, world.random.choice(recharge_options_1))
    options[out[0]].remove(out[1])

    options |= {"m020_013": [3, 7, 9]}
    tackle_2_options = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.TACKLE, level=2), max_health
    )
    out = apply_place_on_random(world, options, world.random.choice(tackle_2_options))
    options[out[0]].remove(out[1])

    options["m020_013"] += [1, 2, 4, 5, 6, 8, 10, 11, 12]
    options |= {
        "m020_003": [1, 3, 4],
        "m020_007": [0, 1, 2],
        "m020_004": [0, 1],
    }

    cut_2_options = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.CUT, level=2), max_health
    )
    out = apply_place_on_random(world, options, world.random.choice(cut_2_options))
    options[out[0]].remove(out[1])
    out = apply_place_on_random(world, options, world.random.choice(recharge_options_2))
    options[out[0]].remove(out[1])

    options |= {"m020_011": [0, 1]}
    out = apply_place_on_random(world, options, world.random.choice(recharge_options_1))
    options[out[0]].remove(out[1])

    #  cut 2 counts for the rope cut 1
    flash = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.FLASH, level=1), max_health
    )
    flash_mon = world.random.choice(flash)
    assert flash_mon == 65  # has to be electabuzz for now without script changes
    out = apply_place_on_random(world, options, flash_mon)
    options[out[0]].remove(out[1])

    if world.options.randomize_pokemon_etc != RandomizePokemonEtc.option_vanilla:
        place_npc(world, ("m001_014", 5), flash_mon)

    # after flash + cut 1 ( not relevant)
    options["m020_003"] += [0, 2]

    last_one = {"m020_016": [0]}
    apply_place_on_random(world, last_one, world.random.choice(tackle_2_options))

    """mission 9 drifblim"""
    max_health = 5000
    options = {
        "m023_006": [0, 1, 2],
        "m023_007": [0, 1],
    }
    elevate_users = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.ELEVATE, level=1), max_health
    )
    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True

    # m023_011 - 7, 0, 4
    # m023_013 - 2, 4, 3

    m023_013 = [2, 3, 4]
    options = {"m023_013": m023_013}
    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True
    m023_013.remove(out[1])

    options = {
        "m023_011": [1, 2, 3, 5, 6],
    }
    crush_2 = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.CRUSH, level=2), max_health
    )
    out = apply_place_on_random(world, options, world.random.choice(crush_2))
    options[out[0]].remove(out[1])

    options["m023_011"] += [0, 4, 7]
    options["m023_013"] = m023_013

    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True

    options = {"m023_015": [0, 1]}
    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True


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
    world.modified_regions[to_map].modified = True


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

    #  since they already swapped things I need to confirm
    #  if the two bidoofs match in position or need to swap.
    m001_005_to_m001_014 = {0: 1, 1: 0, 2: 2, 3: 3}
    # #  rampardos
    # copy_over_spawn_to_npc(world, "m016_004", 2, "m016_004", 0)
    # copy_over_spawn_to_npc(world, "m016_004", 2, "m016_004", 1)

    return


def apply_randomize_npc_pokemon(world: PokemonRSOA) -> None:
    groups: List[List[Tuple[str, int]]] = [
        # --- mission interactions
        # consider making the drifloon groups the same???
        [
            ("m201_001", 2),
            ("m201_001", 3),
            ("m201_001", 4),
            ("m201_001", 5),
        ],  # m8 drifloon water
        [("m018_001", i) for i in range(0, 5)],  # m8 drifloon boyleland
        [("m019_013", 0), ("m019_013", 1)],  # m8 drifloon left side
        # ---
        [("m020_014", 1)],  # m8 kidnapped magmar
        [("m020_014", 2), ("m020_009", 2), ("m001_014", 6)],  # m8 kidnapped pikachu
        [
            ("m019_002", 6),
            ("m019_002", 7),
            ("m019_002", 8),
            ("m020_014", 3),
            ("m020_014", 4),
            ("m020_013", 5),
            ("m020_009", 2),
        ],  # m8 kidnapped charmander
        [
            ("m019_002", 9),
            ("m019_002", 10),
            ("m019_002", 11),
            ("m020_014", 5),
            ("m020_014", 6),
        ],  # m8 kidnapped slugma
        [("m020_014", 7), ("m020_014", 8)],  # m8 kidnapped stunky
        [("m020_008", 0)],  # m8 gliscor fly away
        [("m015_001", 11)],  # q12 budew
        [("m018_001", 21)],  # spinning mime jr
        [("m018_001", 22)],  # spinned around bidoof
    ]

    groups += [
        # --- partners
        [
            ("m020_006", 2),
            ("m020_009", 8),
            ("m001_014", 8),
        ],  # m8 barlow Makuhita
        #  skipped out on the Wendy Staraptor, as it's flying, requires testing
        [("m017_004", 13)],  # m9 keith Buizel
        [("m023_014", 12)],  # m9 sven Luxray
    ]

    if world.modified_regions["m020_013"].modified:
        #  made the npcs somewhat the same as the mons that appear in the actual map,
        #  as these are the pokemon that should be running away in m8 cutscene
        #  doing it randomly however rather than setting the exact ones.
        #  purugly and vulpix
        copy_over_spawn_to_npc(world, "m020_007", 2, "m019_002", 16)
        copy_over_spawn_to_npc(world, "m020_007", 1, "m019_002", 17)

        for i in [0, 1, 2, 3]:
            j = world.random.randint(1, 12)
            copy_over_spawn_to_npc(world, "m020_013", j, "m020_011", i)

        for i in [0, 1, 2, 3, 4]:
            #  the two magcargo are weird as they have no logical origin source
            j = world.random.randint(0, 12)
            copy_over_spawn_to_npc(world, "m020_002", j, "m020_013", i)

        for i in [4, 5, 6]:
            j = world.random.randint(1, 12)
            copy_over_spawn_to_npc(world, "m020_013", j, "m020_009", i)

        copy_over_spawn_to_npc(world, "m020_013", 8, "m001_014", 9)

    pokemon = world.random.choices(list(world.modified_species.keys()), k=len(groups))

    for group, mon in zip(groups, pokemon):
        form_id = list(world.modified_species[mon].forms.keys())[0]
        for place in group:
            place_npc(world, place, form_id)
