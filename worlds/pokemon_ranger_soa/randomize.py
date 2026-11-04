from __future__ import annotations

from collections import defaultdict
from typing import Dict, TYPE_CHECKING, Optional, List, Tuple

from BaseClasses import ItemClassification, CollectionState
from Fill import fill_restrictive
from .MonSelect import (
    add_to,
    MonPlacer,
    get_required_fieldmove,
    apply_place_on_random,
    form_options_by_criteria,
    add_to_normal,
)
from .data import SpeciesData, data, FieldMove, Party, FieldMoveCategory
from .events import PInstanceEvent
from .items import PokemonRSOAItem
from .options import (
    RandomizePartners,
    partner_blacklist,
    RandomizePokemonEtc,
    RandomizePokemonEncounters,
    FieldMoveItem,
)

if TYPE_CHECKING:
    from .world import PokemonRSOA


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
    additional_blacklist = world.options.blacklist_random_mons.get_blacklist("partner")

    allowed_partners = [
        i
        for i in [*range(1, 267), 435, 436, 437]
        if i not in partner_blacklist and i not in additional_blacklist
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

    starters = [list(data.species[i].forms.keys())[0] for i in starters]
    partners = [list(data.species[i].forms.keys())[0] for i in partners]

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
        244,  # sneasel
        220,  # misdreavus
        #
        161,  # machop
        246,  # hippopotas
        251,  # gible
    ]
    if starters_only:
        world.blacklisted_captures |= set(vanilla_partners_in_some_order)
        world.modified_partners = starters + [
            list(data.species[i].forms.keys())[0]
            for i in vanilla_partners_in_some_order
        ]
        return
    # kricketot
    place_npc(world, ("m008_006", 8), 314)
    place_npc(world, ("m008_006", 12), 314)
    PInstanceEvent.KRICKETOT.form_id = partners[0]

    # cranidos
    place_npc(world, ("m008_006", 9), 315)
    place_npc(world, ("m016_003", 1), 315)
    PInstanceEvent.CRANIDOS.form_id = partners[1]

    # turtwig
    place_npc(world, ("m008_008", 0), 316)
    place_npc(world, ("m004_007", 0), 316)
    PInstanceEvent.TURTWIG.form_id = partners[2]

    # croagunk
    place_npc(world, ("m008_008", 2), 317)
    place_npc(world, ("m002_001", 9), 317)
    PInstanceEvent.CROAGUNK.form_id = partners[3]

    # mime jr
    place_npc(world, ("m008_008", 4), 318)
    place_npc(world, ("m001_014", 7), 318)
    place_npc(world, ("m019_002", 15), 318)
    place_npc(world, ("m020_002", 0), 318)
    place_npc(world, ("m020_005", 1), 318)
    place_npc(world, ("m020_009", 7), 318)
    place_npc(world, ("m020_014", 0), 318)
    place_npc(world, ("m020_016", 1), 318)
    place_npc(world, ("m018_001", 21), 318)  # post capture and such
    PInstanceEvent.MIME_JR.form_id = partners[4]

    # shieldon
    place_npc(world, ("m008_006", 9), 319)
    place_npc(world, ("m016_003", 1), 319)
    PInstanceEvent.SHIELDON.form_id = partners[5]

    # chimchar
    place_npc(world, ("m008_008", 1), 320)
    place_npc(world, ("m022_001", 4), 320)
    PInstanceEvent.CHIMCHAR.form_id = partners[6]

    # piplup
    place_npc(world, ("m008_008", 7), 321)
    place_npc(world, ("m026_001", 10), 321)
    PInstanceEvent.PIPLUP.form_id = partners[7]

    # snover
    place_npc(world, ("m008_008", 3), 322)
    place_npc(world, ("m019_005", 1), 322)
    PInstanceEvent.SNOVER.form_id = partners[8]

    # sneasel
    place_npc(world, ("m008_006", 3), 323)
    place_npc(world, ("m028_009", 1), 323)
    PInstanceEvent.SNEASEL.form_id = partners[9]

    # misdreavus
    place_npc(world, ("m008_006", 7), 324)
    place_npc(world, ("m023_005", 0), 324)
    PInstanceEvent.MISDREAVUS.form_id = partners[10]

    ...
    #  TODO change the partner encounter events
    world.modified_partners = starters + partners


def early_place_random_restricted(world: PokemonRSOA) -> Tuple[MonPlacer, ...]:
    mission_goal = world.get_rule_num()
    """place special crush 1 and cut 1 in school"""
    if world.options.field_move_item != FieldMoveItem.option_vanilla:
        bidoof = 328
        zubat = 329
    else:
        max_health = 100
        bidoof = world.random.choice(
            form_options_by_criteria(
                world, FieldMove(category=FieldMoveCategory.CRUSH, level=1), max_health
            )
        )
        zubat = world.random.choice(
            form_options_by_criteria(
                world, FieldMove(category=FieldMoveCategory.CUT, level=1), max_health
            )
        )
        #  TODO on low goals, this randomized bidoof and
        #   zubat mon are not guaranteed to be items!

    options = {
        "m001_004": [1],
        "m001_006": [0],
        "m001_008": [0, 1, 2, 3, 4],
    }
    out = apply_place_on_random(world, options, bidoof)
    options[out[0]].remove(out[1])
    options["m001_004"] += [0]
    options |= {
        "m001_007": [0, 1, 2, 3],
    }
    apply_place_on_random(world, options, zubat)

    maps = MonPlacer(world)
    maps.all_maps |= {
        #  mission 0, 1
        "m001_001": [0, 1, 3, 4],
        "m001_002": [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11],
        "m001_003a": [0, 1, 2],
        "m001_005": [0, 1, 2, 3],
        "m001_009": [0],
        "m001_011": [4],
        "m001_015": [0],
        "m003_001": [1, 2, 4],
        "m007_001": [1, 3, 4],
    }

    tree_fieldmove = get_required_fieldmove(world, "m001_001", 5)
    tree_spots = [("m001_001", 5), ("m007_001", 4)]
    maps.add_requires(tree_fieldmove, tree_spots)
    # bonsly
    maps.add_requires(get_required_fieldmove(world, "m001_002", 3), [("m001_002", 7)])
    # tangrowth
    maps.add_requires(get_required_fieldmove(world, "m001_001", 0), [("m001_015", 0)])

    if mission_goal <= 0:
        return (maps,)

    maps.all_maps |= {"m005_001b": [0, 1, 2, 3, 4, 5]}
    marine_cave_fence = get_required_fieldmove(world, "m006_001", 2)
    maps.place_random(
        fieldmove=marine_cave_fence, max_health=world.mission_affinities[1]
    )

    maps.all_maps |= {
        "m006_002": [0, 1, 2, 3, 4, 5, 6, 7],
        "m006_003": [0],
        "m006_004": [0],
    }
    maps.add_requires(get_required_fieldmove(world, "m006_001", 1), [("m006_003", 0)])
    maps.add_requires(get_required_fieldmove(world, "m006_002", 0), [("m006_004", 0)])

    red_gigaremo = get_required_fieldmove(world, "m006_001", 0)
    maps.place_random(fieldmove=red_gigaremo, max_health=world.mission_affinities[1])

    if mission_goal <= 2:
        return (maps,)

    maps.all_maps |= {
        "m006_001": [0, 1, 2, 3, 4, 5, 6],
        "m009_002": [2, 4, 5, 8, 11, 19],
        "m009_001a": [5],
    }
    maps.add_requires(tree_fieldmove, [("m009_002", 19), ("m009_002", 20)])

    burning_log = get_required_fieldmove(world, "m009_002", 5)
    maps.place_random(fieldmove=burning_log, max_health=world.mission_affinities[2])

    maps.all_maps["m009_002"] += [0, 1, 3, 6, 7, 9, 10, 13, 16, 17, 18, 20, 21]
    maps.add_requires(tree_fieldmove, [("m009_002", 21)])

    maps.place_random(form_id=211)  # fetch happiny!

    maps.all_maps["m009_001a"] += [0, 1, 2, 3, 4]
    maps.all_maps |= {
        "m009_009": [0, 1],
        "m009_004": [8],
    }
    maps.add_requires(tree_fieldmove, [("m009_002", 21)])

    rain_dance = FieldMove(category=FieldMoveCategory.RAIN_DANCE, level=1)
    maps.place_random(fieldmove=rain_dance, max_health=world.mission_affinities[2])

    if mission_goal <= 3:
        return (maps,)
    maps.requires_forms_one.append(186)  # fetch combee quest 03
    maps.add_requires(get_required_fieldmove(world, "m009_002", 2), [])  # quest 11
    maps.add_requires(get_required_fieldmove(world, "m005_001b", 1), [])  # quest 49
    maps.add_requires(get_required_fieldmove(world, "m009_011", 0), [])  # quest 4

    maps.all_maps |= {
        "m009_001b": [2, 3, 4, 8],
        "m009_008": [*range(0, 14)],
        "m009_011": [0, 1, 2, 3, 4],
        "m009_012": [1, 2],
    }

    maps.add_requires(
        get_required_fieldmove(world, "m009_008", 1),
        [("m009_008", 4), ("m009_008", 5)],
    )

    green_gigaremo_right = get_required_fieldmove(world, "m010_002", 14)
    green_gigaremo_left = get_required_fieldmove(world, "m010_022", 4)
    blue_gigaremo = get_required_fieldmove(world, "m010_002", 20)
    red_gigaremo_middle = get_required_fieldmove(world, "m010_001", 3)
    gate_right = get_required_fieldmove(world, "m010_002", 19)
    gate_left = get_required_fieldmove(world, "m010_022", 11)

    max_health = world.mission_affinities[3]

    choice = world.random.randint(0, 2)
    if choice == 0:
        maps.place_random(fieldmove=gate_right, max_health=max_health)
    if choice == 1:
        maps.place_random(fieldmove=gate_left, max_health=max_health)
        maps.all_maps |= {
            "m010_016": [0],
        }
        maps.place_random(fieldmove=green_gigaremo_left, max_health=max_health)
        maps.all_maps |= {
            "m010_022": [0, 1, 2, 3, 4, 5, 7, 8],
        }
    if choice == 2:
        maps.place_random(fieldmove=red_gigaremo_middle, max_health=max_health)
        maps.all_maps |= {
            "m010_001": [0, 1, 2, 3, 4, 5],
            "m010_016": [0],
        }
        maps.place_random(fieldmove=green_gigaremo_left, max_health=max_health)
        maps.all_maps |= {
            "m010_022": [0, 1, 2, 3, 4, 5, 7, 8],
        }
        maps.all_maps["m010_001"] += [6]
    print("choice made mission 4:", choice)

    maps.all_maps["m010_007"] = [0]
    maps.place_random(fieldmove=green_gigaremo_right, max_health=max_health)
    maps.place_random(fieldmove=blue_gigaremo, max_health=max_health)
    if mission_goal <= 4:
        return (maps,)

    maps.add_requires(get_required_fieldmove(world, "m005_001b", 0), [])  # quest 2

    if choice == 0:
        maps.all_maps |= {
            "m010_001": [0, 1, 2, 3, 4, 5, 6],
            "m010_022": [0, 1, 2, 3, 4, 5, 7, 8],
            "m010_016": [0],
        }
    if choice == 1:
        maps.all_maps["m010_001"] = [0, 1, 2, 3, 4, 5, 6]
    maps.all_maps |= {
        "m010_002": [0, 1, 2, 4, 5, 6, 7, 8, 9],
        "m010_003": [0, 1, 2, 3, 5, 6, 7, 9, 10, 12, 13, 14],
    }

    sea = MonPlacer(world)
    sea.all_maps |= {
        "m011_001": [i for i in range(0, 11) if i not in [6, 8]],
        "m011_002": [0, 1, 3, 5, 8],
        "m011_004": [],
    }
    sea.add_requires(get_required_fieldmove(world, "m011_002", 0), [("m011_002", 9)])

    underwater_fence = get_required_fieldmove(world, "m011_001", 0)
    sea.place_random(fieldmove=underwater_fence, max_health=world.mission_affinities[4])

    sea.all_maps["m011_001"] += [6, 8]
    sea.all_maps |= {
        "m011_003": [*range(0, 9)],
    }

    underwater_fence_2 = get_required_fieldmove(world, "m011_003", 0)
    sea.place_random(
        fieldmove=underwater_fence_2, max_health=world.mission_affinities[4]
    )

    sea.all_maps["m011_003"] += [9, 10, 11]
    sea.all_maps["m011_002"] += [2, 4, 6, 7]

    swim = FieldMove(FieldMoveCategory.SWIM, 1)
    sea.place_random(fieldmove=swim, max_health=world.mission_affinities[4])

    sea.all_maps |= {"m011_004": [1, 2, 3, 0]}

    """place surf in puel sea"""
    options = {"m011_004": [1, 2, 3]}
    form_id = 0x06A
    out = apply_place_on_random(world, options, form_id)
    sea.added_forms.add(form_id)
    sea.all_maps[out[0]].remove(out[1])

    if mission_goal <= 5:
        return maps, sea
    maps.requires_forms_one.append(69)  # fetch eevee quest 08
    lumineon_where = world.random.random() < 0.5  # fetch lumineon quest 05
    if lumineon_where:
        sea.requires_forms_one.append(224)
    else:
        maps.requires_forms_one.append(224)

    sea.all_maps["m011_005"] = [0, 1, 2, 3, 4, 6]
    maps.all_maps |= {
        "m015_001": [2, 3, 4, 5],
        "m015_004": [2, 3, 11],
        "m016_001": [3, 4, 5, 6, 7, 8, 9],
    }
    maps.all_maps["m010_003"] += [11]
    maps.add_requires(tree_fieldmove, [("m015_004", 11)])
    maps.add_requires(get_required_fieldmove(world, "m017_004", 0), [])  # red gig

    vine = get_required_fieldmove(world, "m016_001", 2)
    maps.place_random(fieldmove=vine, max_health=world.mission_affinities[5])

    maps.all_maps["m016_001"] += [0, 1, 2]
    maps.all_maps |= {
        "m016_003": [*range(1, 16)],
    }

    yellow_gigaremo = get_required_fieldmove(world, "m016_002", 0)
    maps.place_random(fieldmove=yellow_gigaremo, max_health=world.mission_affinities[5])
    maps.all_maps |= {
        "m016_002": [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    }

    if mission_goal <= 6:
        return maps, sea

    maps.requires_forms_one.append(133)  # fetch nosepass quest 06
    maps.requires_forms_one.append(195)  # fetch ambipom quest 07
    maps.requires_forms_one.append(22)  # fetch oddish quest 09

    to_add = {
        "m016_004": [0, 1, 3, 4],
        "m015_004": [0, 1, 4, 5, 6, 8, 9, 10],
        "m009_009": [2],
        "m001_011": [5],
    }
    add_to_normal(maps.all_maps, to_add)

    if mission_goal <= 7:
        return maps, sea

    maps.all_maps |= {"m018_001": [1, 2], "m019_001": [1, 6, 7, 8], "m019_013": [0, 1]}

    airlift = FieldMove(FieldMoveCategory.AIRLIFT, level=1)
    maps.place_random(
        fieldmove=airlift, max_health=world.mission_affinities[7], ignore_dupe=True
    )

    to_add = {"m019_001": [2, 3, 5], "m019_003": [2]}
    add_to_normal(maps.all_maps, to_add)
    airlift = FieldMove(FieldMoveCategory.AIRLIFT, level=1)
    maps.place_random(
        fieldmove=airlift, max_health=world.mission_affinities[7], ignore_dupe=False
    )

    to_add = {
        "m019_003": [1, 4, 5, 6, 7],
        "m019_004": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "m019_010": [0],
        "m019_016": [0, 1, 2],
    }
    add_to_normal(maps.all_maps, to_add)

    maps.add_requires(get_required_fieldmove(world, "m019_004", 4), [("m019_010", 0)])
    print("somehow this one is fucked", get_required_fieldmove(world, "m019_004", 4))

    """volcano cave drifloon"""
    options = {
        "m019_003": [1, 4, 5, 6, 7],
        "m019_004": [1, 3, 4, 5, 6, 9],
    }
    out = apply_place_on_random(world, options, 0x0C4)
    maps.remove_if(*out, form_id=0x0C4)
    options = {
        "m019_004": [2, 7, 8],
        "m019_016": [0, 1, 2],
    }
    out = apply_place_on_random(world, options, 0x0C4)
    maps.remove_if(*out, form_id=0x0C4)

    crush_2_rock = get_required_fieldmove(world, "m019_004", 2)
    maps.place_random(fieldmove=crush_2_rock, max_health=world.mission_affinities[7])

    """place the whole ship required section"""
    temp = MonPlacer(world)
    temp.all_maps = {
        "m020_013": [*range(1, 13)],
        "m020_003": [0, 1, 2, 3, 4],
        "m020_007": [0, 1, 2],
        "m020_004": [0, 1],
        "m020_011": [0, 1],
    }
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
    electrify_2 = world.random.choice(form_options)
    out = apply_place_on_random(world, options, electrify_2)
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
    tackle_2 = world.random.choice(tackle_2_options)
    out = apply_place_on_random(world, options, tackle_2)
    options[out[0]].remove(out[1])
    temp.remove_if(*out, form_id=tackle_2)

    options["m020_013"] += [1, 2, 4, 5, 6, 8, 10, 11, 12]
    options |= {
        "m020_003": [1, 3, 4],
        "m020_007": [0, 1, 2],
        "m020_004": [0, 1],
    }

    cut_2_options = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.CUT, level=2), max_health
    )
    cut_2 = world.random.choice(cut_2_options)
    out = apply_place_on_random(world, options, cut_2)
    options[out[0]].remove(out[1])
    temp.remove_if(*out, form_id=cut_2)

    recharge_2 = world.random.choice(recharge_options_2)
    out = apply_place_on_random(world, options, recharge_2)
    options[out[0]].remove(out[1])
    temp.remove_if(*out, form_id=recharge_2)

    options |= {"m020_011": [0, 1]}
    recharge_1 = world.random.choice(recharge_options_1)
    out = apply_place_on_random(world, options, recharge_1)
    options[out[0]].remove(out[1])
    temp.remove_if(*out, form_id=recharge_1)

    #  cut 2 counts for the rope cut 1
    flash = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.FLASH, level=1), max_health
    )
    flash_mon = world.random.choice(flash)
    assert flash_mon == 65  # has to be electabuzz for now without script changes
    out = apply_place_on_random(world, options, flash_mon)
    temp.remove_if(*out, form_id=flash_mon)

    if world.options.randomize_pokemon_etc != RandomizePokemonEtc.option_vanilla:
        place_npc(world, ("m001_014", 5), flash_mon)

    # after flash + cut 1 ( not relevant)
    options["m020_003"] += [0, 2]

    last_one = {"m020_016": [0]}
    out = apply_place_on_random(world, last_one, world.random.choice(tackle_2_options))

    if mission_goal <= 8:
        return maps, sea

    max_health = 5000

    add_to_normal(maps.all_maps, temp.all_maps)
    maps.added_forms |= temp.added_forms
    #  TODO, make these count for field moves too!!!
    del temp

    maps.add_requires(get_required_fieldmove(world, "m001_002", 2), [])  # quest 10
    maps.requires_forms_one.append(192)  # fetch cherrim quest 12
    maps.add_requires(get_required_fieldmove(world, "m019_002", 4), [])  # quest 13
    maps.add_requires(get_required_fieldmove(world, "m019_002", 5), [])  # quest 13
    maps.requires_forms_one.append(45)  # fetch muk quest 14

    maps.all_maps |= {
        "m020_010": [0],
        "m020_014": [0, 1],
        "m021_001": [i for i in range(0, 17) if i not in [6, 9, 11]],
        "m021_002": [1, 2, 3, 4, 5, 6, 7],
        "m022_001": [i for i in range(1, 19) if i not in [8, 10]],
        "m022_003": [0, 2, 3],
    }
    maps.all_maps["m001_002"] += [6, 12]
    maps.add_requires(
        tree_fieldmove, [("m021_001", 14), ("m021_001", 15), ("m021_001", 16)]
    )
    maps.add_requires(
        get_required_fieldmove(world, "m022_001", 6),
        [("m022_003", 0), ("m022_003", 2), ("m022_003", 3)],
    )

    maps.place_random(
        fieldmove=FieldMove(FieldMoveCategory.DEMIST, 1), max_health=max_health
    )

    tackle_3 = get_required_fieldmove(world, "m022_002", 1)
    maps.place_random(fieldmove=tackle_3, max_health=max_health)

    maps.all_maps |= {
        "m023_001": [0, 1, 2, 3],
        "m023_002": [0],
        "m023_003": [0, 1],
        "m023_004": [0, 1, 2],
        "m023_005": [0],
    }
    maps.add_requires(FieldMove(FieldMoveCategory.ELEVATE, 1), [("m023_002", 0)])
    maps.add_requires(get_required_fieldmove(world, "m023_003", 0), [("m023_005", 0)])

    elevate_users = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.ELEVATE, level=1), max_health
    )
    elevate_users = [197]  # because of the quest that only takes one type of driblim...
    place = world.random.choice(elevate_users)

    maps.place_random(FieldMove(FieldMoveCategory.FLASH, 1), max_health=max_health)
    tunnel = get_required_fieldmove(world, "m023_004", 0)
    maps.place_random(fieldmove=tunnel, max_health=max_health)

    maps.all_maps |= {
        "m023_006": [0, 1, 2],  # add umbreon later
        "m023_008": [0],
        "m023_007": [0, 1],
    }
    maps.add_requires(get_required_fieldmove(world, "m023_006", 0), [("m023_008", 0)])

    options = {
        "m023_006": [0, 1, 2],
        "m023_007": [0, 1],
    }
    out = apply_place_on_random(world, options, place)
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True
    maps.all_maps[out[0]].remove(out[1])

    crush_2_rock_2 = get_required_fieldmove(world, "m023_007", 0)
    maps.place_random(fieldmove=crush_2_rock_2, max_health=max_health)

    maps.all_maps |= {
        "m023_009": [0, 1, 2],
    }
    tunnel_again = get_required_fieldmove(world, "m023_009", 0)
    maps.place_random(fieldmove=tunnel_again, max_health=max_health)

    maps.all_maps |= {
        "m023_011": [0, 1, 2, 3, 4, 5, 6, 7],
        "m023_013": [2, 4, 3],
        "m023_012": [0],
        "m023_010": [0],
    }
    maps.all_maps["m023_006"] += [3]
    maps.add_requires(get_required_fieldmove(world, "m023_011", 1), [("m023_012", 0)])
    maps.add_requires(get_required_fieldmove(world, "m023_006", 1), [("m023_010", 0)])

    # m023_011 - 7, 0, 4
    # m023_013 - 2, 4, 3
    """placing drifblim!"""
    m023_013 = [2, 3, 4]
    options = {"m023_013": m023_013}
    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True
    maps.all_maps[out[0]].remove(out[1])
    m023_013.remove(out[1])

    options = {
        "m023_011": [1, 2, 3, 5, 6],
    }
    crush_2 = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.CRUSH, level=2), max_health
    )
    """TODO IMPORTANT!!!, when randomizing fieldmove, 
    this needs to stay an already before mandatory required fieldmove
    else this turns into a softlock :)
    """
    out = apply_place_on_random(world, options, world.random.choice(crush_2))
    options[out[0]].remove(out[1])
    maps.all_maps[out[0]].remove(out[1])

    options["m023_011"] += [0, 4, 7]
    options["m023_013"] = m023_013

    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True
    maps.all_maps[out[0]].remove(out[1])

    tunnel_again = get_required_fieldmove(world, "m023_011", 0)
    maps.place_random(fieldmove=tunnel_again, max_health=max_health)

    maps.all_maps["m023_013"] += [1]

    tackle_3_again = get_required_fieldmove(world, "m023_013", 0)
    maps.place_random(fieldmove=tackle_3_again, max_health=max_health)

    maps.all_maps["m023_013"] += [0]

    maps.place_random(
        fieldmove=FieldMove(FieldMoveCategory.STINK, 1), max_health=max_health
    )

    maps.all_maps |= {
        "m023_015": [0, 1],
        "m023_016": [0],
    }
    maps.add_requires(get_required_fieldmove(world, "m023_016", 0), [("m023_016", 0)])

    options = {
        "m023_015": [0, 1],
    }
    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True
    maps.all_maps[out[0]].remove(out[1])

    if mission_goal <= 9:
        return maps, sea

    maps.requires_forms_one.append(91)  # fetch murkrow quest 15
    maps.requires_forms_dupe.append(91)  # fetch murkrow quest 15

    max_health = world.mission_affinities[9]
    to_add = {
        "m023_014": [0, 1, 2],
        "m010_002": [3],
        "m010_022": [6],
        "m021_001": [6],
        "m009_009": [3],
        "m015_004": [7],
    }
    add_to_normal(maps.all_maps, to_add)

    maps.place_random(
        fieldmove=FieldMove(FieldMoveCategory.RIVER_FLOW, 1), max_health=max_health
    )

    """Vien forest west"""
    to_add = {
        "m009_003": [0, 1, 4, 5, 6, 7, 8, 10, 11],
        "m009_004": [i for i in range(0, 11) if i not in [0, 8]],
        "m009_006": [0],
    }
    add_to_normal(maps.all_maps, to_add)
    maps.add_requires(get_required_fieldmove(world, "m009_006", 0), [("m009_006", 0)])

    options = {"m009_004": [3, 5, 7, 9]}  # also 0 for staraptor
    floatzel = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.RIVER_FLOW, level=1), max_health
    )
    out = apply_place_on_random(world, options, world.random.choice(floatzel))
    maps.all_maps[out[0]].remove(out[1])

    options = {
        "m009_003": [0, 1, 4, 5, 6, 7, 8, 10, 11],
        "m009_004": [1, 2, 4, 6, 10],
    }
    out = apply_place_on_random(world, options, world.random.choice(floatzel))
    maps.all_maps[out[0]].remove(out[1])

    """crysta cave"""
    base_options = {
        "m024_001": [0, 1, 2],
        "m024_002": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "m024_004": [0, 1],
        "m024_005": [0],
    }
    add_to_normal(maps.all_maps, base_options)

    out = apply_place_on_random(world, base_options, world.random.choice(floatzel))
    maps.all_maps[out[0]].remove(out[1])

    options = {"m024_001": [3, 4, 6]}
    add_to_normal(maps.all_maps, options)

    out = apply_place_on_random(world, options, world.random.choice(floatzel))
    maps.all_maps[out[0]].remove(out[1])

    options = {
        "m024_003": [0],
        "m024_006": [0],
    }
    add_to_normal(maps.all_maps, options)

    out = apply_place_on_random(world, options, world.random.choice(floatzel))
    maps.all_maps[out[0]].remove(out[1])

    solid_ice = get_required_fieldmove(world, "m024_004", 1)
    maps.place_random(fieldmove=solid_ice, max_health=max_health)

    maps.all_maps |= {
        "m024_007": [0, 1, 2, 3, 4],
        "m026_001": [*range(0, 13)],
        "m027_001": [0],
    }

    snow_tree = get_required_fieldmove(world, "m026_001", 2)
    maps.add_requires(snow_tree, [("m026_001", 11), ("m026_001", 12)])

    maps.place_random(
        fieldmove=FieldMove(FieldMoveCategory.RIVER_FLOW, 2), max_health=max_health
    )

    maps.all_maps |= {
        "m027_002": [0, 1, 2, 4, 5, 6, 8],
    }

    empoleon = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.RIVER_FLOW, level=2), max_health
    )
    options = {
        "m027_002": [5, 8],
    }
    out = apply_place_on_random(world, options, world.random.choice(empoleon))
    maps.all_maps[out[0]].remove(out[1])

    options = {
        "m027_002": [0, 1, 2, 4, 6],  # exclude staraptor 3
    }
    out = apply_place_on_random(world, options, world.random.choice(empoleon))
    maps.all_maps[out[0]].remove(out[1])

    torch_1 = get_required_fieldmove(world, "m027_002", 1)
    maps.place_random(fieldmove=torch_1, max_health=max_health)

    maps.all_maps |= {
        "m028_006": [0, 1],
        "m028_001": [0, 1, 2, 3, 4],
        "m028_002": [0, 1],
        "m028_004": [0, 1],
        "m028_005": [0, 1, 2],
        "m028_012": [0, 1],
        "m028_013": [0],
        "m028_009": [0, 1, 2],
        "m028_010": [0, 1],
        "m028_011": [1, 2],
    }
    maps.add_requires(
        get_required_fieldmove(world, "m028_013", 1),
        [
            ("m028_009", 0),
            ("m028_009", 1),
            ("m028_009", 2),
            ("m028_010", 0),
            ("m028_010", 1),
        ],
    )

    big_iceee = get_required_fieldmove(world, "m028_001", 1)
    maps.place_random(fieldmove=big_iceee, max_health=max_health)

    maps.all_maps["m028_011"] += [0]
    maps.all_maps |= {
        "m028_018": [1],
        "m028_019": [0, 1, 2, 3],
        "m028_020": [0],
        "m028_003": [0, 1, 3],
        "m028_017": [0, 1],
    }

    second_toch = get_required_fieldmove(world, "m028_017", 1)
    maps.place_random(fieldmove=second_toch, max_health=max_health)
    maps.all_maps |= {
        "m028_024": [0, 1],
    }
    maps.add_requires(get_required_fieldmove(world, "m028_024", 1), [("m028_024", 0)])
    #  could also just rework that one spot can be in multiple requires if I want to

    door_3 = get_required_fieldmove(world, "m028_020", 2)
    maps.place_random(fieldmove=door_3, max_health=max_health)

    maps.all_maps["m028_018"] += [0, 2]
    maps.all_maps |= {"m028_016": [0, 1]}

    maps.place_random(form_id=216)  # fetch riolu
    maps.place_random(form_id=216, ignore_dupe=False)  # fetch riolu

    if mission_goal <= 10:
        return maps, sea
    """mission 11"""

    maps.requires_forms_one.append(204)  # fetch chingling quest 17
    maps.requires_forms_one.append(227)  # fetch abomasnow quest 18
    maps.add_requires(get_required_fieldmove(world, "m024_004", 2), [])  # quest 19

    max_health = world.mission_affinities[10]

    maps.all_maps |= {
        "m019_005": [6],
    }
    maps.place_random(FieldMove(FieldMoveCategory.MAGMA_FLOW, 1), max_health)

    to_add = {
        "m019_005": [1, 2, 3, 4, 5, 7],
        "m019_017": [0, 1, 2],
        "m019_001": [0, 4],
        "m019_003": [0],
        "m019_015": [0],
    }
    add_to_normal(maps.all_maps, to_add)

    torkoal = form_options_by_criteria(
        world, FieldMove(category=FieldMoveCategory.MAGMA_FLOW, level=1), max_health
    )

    options = {
        "m019_005": [1, 2, 3, 5, 7],
        "m019_017": [0, 1, 2],
    }
    out = apply_place_on_random(world, options, world.random.choice(torkoal))
    maps.remove_if(*out)

    options = {"m019_003": [0], "m019_015": [0]}
    out = apply_place_on_random(world, options, world.random.choice(torkoal))
    maps.remove_if(*out)

    rock_1 = get_required_fieldmove(world, "m019_005", 0)
    maps.place_random(fieldmove=rock_1, max_health=max_health)
    rock_2 = get_required_fieldmove(world, "m019_005", 1)
    maps.place_random(fieldmove=rock_2, max_health=max_health)

    maps.all_maps["m019_005"] += [0]
    maps.all_maps |= {
        "m019_006": [5, 6, 7],
        "m019_014": [0, 1],
    }

    fire_wall = get_required_fieldmove(world, "m019_006", 26)
    maps.place_random(fieldmove=fire_wall, max_health=max_health)

    maps.all_maps["m019_006"] += [1, 2, 3, 4]
    maps.all_maps |= {
        "m019_007": [
            0,
            3,
            4,
            7,
        ]
    }
    rock_1 = get_required_fieldmove(world, "m019_007", 2)
    maps.place_random(fieldmove=rock_1, max_health=max_health)
    rock_2 = get_required_fieldmove(world, "m019_007", 1)
    maps.place_random(fieldmove=rock_2, max_health=max_health)
    maps.all_maps["m019_007"] += [5, 6]
    rock_idk = get_required_fieldmove(world, "m019_007", 0)
    maps.place_random(fieldmove=rock_idk, max_health=max_health)
    maps.all_maps["m019_007"] += [1, 2]

    options = {"m019_007": [5, 6]}
    out = apply_place_on_random(world, options, world.random.choice(torkoal))
    maps.remove_if(*out)

    """DO I REALLY EXPECT THEM TO GO DOWN TO GRAB THEIR DRIFBLIM???"""
    maps.all_maps |= {"m019_011": [1]}

    if mission_goal <= 11:
        return maps, sea

    max_health = world.mission_affinities[11]

    # done by not having drifblims field move randomized
    # maps.requires_forms_one.append()  # fetch drifblim quest 20

    maps.add_requires(get_required_fieldmove(world, "m019_003", 0), [])  # quest 21
    maps.add_requires(get_required_fieldmove(world, "m025_001", 5), [])  # quest 22

    sea.all_maps |= {
        "m029_001": [0, 1, 2, 3, 4, 5],
    }

    crush_4_1 = get_required_fieldmove(world, "m029_001", 5)
    sea.place_random(fieldmove=crush_4_1, max_health=max_health)

    sea.all_maps |= {
        "m029_002": [3, 4, 5, 6],
    }
    crush_4_2 = get_required_fieldmove(world, "m029_002", 20)
    sea.place_random(fieldmove=crush_4_2, max_health=max_health)

    sea.all_maps["m029_002"] += [0, 1, 2]
    # this is where I would put a swim if I was nice
    sea.all_maps |= {
        "m029_003": [0, 1, 2, 3, 4, 5, 7, 8, 9],
    }

    cut_3 = world.random.choice(
        form_options_by_criteria(
            world, FieldMove(category=FieldMoveCategory.CUT, level=3), max_health
        )
    )
    options = {
        "m029_003": [0, 1, 2, 3, 4, 5, 7, 8, 9],
    }
    out = apply_place_on_random(world, options, cut_3)
    sea.remove_if(*out, form_id=cut_3)
    #  could have also placed swim, but I'll be nice for once!!!
    #  should probably still place swim in sea of wailord :)

    cut_3_again_but_i_can_change_it = get_required_fieldmove(world, "m029_003", 3)
    sea.place_random(fieldmove=cut_3_again_but_i_can_change_it, max_health=max_health)

    sea.all_maps["m029_003"] += [6]

    tackle_4 = get_required_fieldmove(world, "m029_003", 1)
    sea.place_random(fieldmove=tackle_4, max_health=max_health)
    sea.all_maps |= {"m029_004": [0, 1, 2, 3, 4, 6, 7]}
    sea.add_requires(get_required_fieldmove(world, "m029_004", 0), [("m029_004", 0)])

    second_last_pillar = get_required_fieldmove(world, "m029_003", 7)
    sea.place_random(fieldmove=second_last_pillar, max_health=max_health)

    last_pillar = get_required_fieldmove(world, "m029_001", 17)
    sea.place_random(fieldmove=last_pillar, max_health=max_health)

    if mission_goal <= 12:
        return maps, sea

    max_health = world.mission_affinities[12]

    sea.all_maps |= {
        "m029_007": [0, 3, 5],
        "m029_008": [4, 6],
        "m029_005": [0],
    }
    maps.all_maps |= {
        "m030_004": [0],
        "m030_005": [0, 2],
        "m030_006": [0, 1],
        "m030_007": [0, 1, 2],
        "m030_008": [0, 1, 2, 3],
    }
    maps.add_requires(
        get_required_fieldmove(world, "m030_005", 2),
        [("m030_008", i) for i in range(4)],
    )

    electrify_3 = get_required_fieldmove(world, "m030_006", 1)
    maps.place_random(electrify_3, max_health=max_health)

    maps.all_maps["m030_005"] += [1]
    maps.all_maps |= {
        "m030_010": [*range(0, 8)],
        "m030_011": [0],
    }

    # idk why I even place this, id never change this one
    maps.place_random(FieldMove(FieldMoveCategory.STINK, 1), max_health=max_health)
    maps.all_maps |= {
        "m030_017": [0, 1, 2, 4, 5, 6, 7],
        "m030_018": [0],
    }

    machine_1 = get_required_fieldmove(world, "m030_018", 1)
    maps.place_random(fieldmove=machine_1, max_health=max_health)
    machine_1 = get_required_fieldmove(world, "m030_019", 1)
    maps.place_random(fieldmove=machine_1, max_health=max_health)
    maps.all_maps["m030_017"] += [3]
    machine_1 = get_required_fieldmove(world, "m030_020", 1)
    maps.place_random(fieldmove=machine_1, max_health=max_health)

    maps.all_maps |= {
        "m030_021": [0],
    }

    if mission_goal <= 13:
        return maps, sea

    chance = world.random.random()  # fetch omastar quest 24
    if chance < 0.5:
        sea.requires_forms_one.append(74)
    else:
        maps.requires_forms_one.append(74)
    maps.requires_forms_one.append(144)  # fetch cacturne quest 25
    maps.add_requires(get_required_fieldmove(world, "m009_002", 2), [])  # quest 11

    max_health = world.mission_affinities[13]

    maps.all_maps |= {
        "m034_001": [4, 6, 8],
    }

    village = get_required_fieldmove(world, "m033_001", 7)
    maps.place_random(fieldmove=village, max_health=max_health)

    maps.all_maps["m034_001"] += [0, 1, 2, 9, 15, 18, 19]
    vine_again = get_required_fieldmove(world, "m034_001", 0)
    maps.place_random(fieldmove=vine_again, max_health=max_health)
    maps.all_maps["m034_001"] += [3, 5, 7, 12, 13, 14, 16]
    maps.all_maps["m035_001"] = [0]

    #  todo if pokemon fieldmoves are randomized and stuff yes place this here
    # however rn this is troll by adding an hippowdon somewhere.

    # from here the quests are possible, crazy
    #  Since the omastar spot only becomes accessible once
    #  you start the omastar quest, and the quest becomes accessible on lumineon capture
    #  the lumineon can NOT be in m029_004.5
    #  I could improve my algorithms to add exclude when setting the place forms
    #  but I don't want or need to right now.
    if lumineon_where:
        sea.place_random(form_id=224, ignore_dupe=True)
    else:
        maps.place_random(form_id=224, ignore_dupe=True)
    sea.all_maps["m029_004"] += [5]
    maps.all_maps |= {
        "m036_001": [0, 1, 2, 3],
        "m036_004": [0, 1, 2, 3, 4, 5],
        "m036_021": [0, 1],
        "m036_005": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "m036_007": [0],
    }

    #  they have enough drifblim available right?

    maps.all_maps |= {
        "m036_012": [0, 1, 2],
        "m036_015": [0],
    }

    tunnel_again_again = get_required_fieldmove(world, "m036_012", 9)
    maps.place_random(fieldmove=tunnel_again_again, max_health=max_health)

    maps.all_maps |= {
        "m036_009": [0, 1, 2, 4, 5, 6],
        "m036_011": [0, 1, 2, 3],
        "m036_020": [0],
        "m036_013": [1, 2],
        "m036_014": [0],
    }

    big_rock = get_required_fieldmove(world, "m036_013", 0)
    maps.place_random(fieldmove=big_rock, max_health=max_health)

    maps.all_maps |= {
        "m036_016": [0, 1, 2, 3, 4],
    }

    options = {"m036_016": [0, 1, 2, 3, 4]}
    out = apply_place_on_random(world, options, world.random.choice(elevate_users))
    world.modified_regions[out[0]].POKEMON_SPAWN[out[1]].missable = True
    maps.remove_if(*out)

    if mission_goal <= 14:
        return maps, sea

    maps.all_maps["m028_003"] += [2]

    maps.requires_forms_one.append(54)  # fetch weezing quest 26
    maps.requires_forms_one.append(206)  # fetch skuntank quest 26
    maps.requires_forms_one.append(403)  # fetch dragonair quest 28

    if mission_goal <= 15:
        return maps, sea

    max_health = world.mission_affinities[15]
    maps.all_maps |= {
        "m038_010": [0],
        "m038_003": [0, 1, 2, 3, 4, 5],
        "m038_006": [0, 1],
        "m038_011": [0, 1],
        "m038_007": [0, 1],
    }

    # flash already loong exists

    beam_you_already_have = get_required_fieldmove(world, "m038_003", 11)
    maps.place_random(fieldmove=beam_you_already_have, max_health=max_health)
    maps.all_maps |= {
        "m038_009": [0, 1],
        "m038_012": [1, 2],
        "m038_015": [1, 2],
        "m038_005": [1, 2],
    }

    doesnot_matter = world.random.randint(0, 1)
    left = get_required_fieldmove(world, "m038_015", 1)
    right = get_required_fieldmove(world, "m038_005", 1)
    if doesnot_matter:
        maps.place_random(fieldmove=left, max_health=max_health)
        maps.all_maps["m038_015"] += [0]
        maps.all_maps["m038_012"] += [0]
        maps.place_random(fieldmove=right, max_health=max_health)
    else:
        maps.place_random(fieldmove=right, max_health=max_health)
        maps.place_random(fieldmove=left, max_health=max_health)
        maps.all_maps["m038_015"] += [0]
        maps.all_maps["m038_012"] += [0]
    maps.all_maps |= {
        "m039_001": [0, 1, 2, 3],
        "m039_003a": [0, 1, 2],
    }

    maps.place_random(
        fieldmove=get_required_fieldmove(world, "m039_004a", 0), max_health=max_health
    )

    maps.all_maps |= {
        "m039_005a": [0, 1, 2],
    }

    maps.place_random(
        fieldmove=get_required_fieldmove(world, "m039_006a", 0), max_health=max_health
    )
    maps.all_maps |= {
        "m039_007a": [0, 1, 2],
    }
    maps.place_random(
        fieldmove=get_required_fieldmove(world, "m039_006a", 0), max_health=max_health
    )
    maps.all_maps |= {
        "m039_002": [0, 1],
        "m039_009": [0],
    }

    return maps, sea


def early_place_random_event_mon(world: PokemonRSOA, maps: MonPlacer):
    mission_goal = world.get_rule_num()
    ...  # randomizer parts

    PInstanceEvent.TUT_BIDOOF.form_id = 427
    PInstanceEvent.SLAKOTH.form_id = 427
    PInstanceEvent.NIGHT_GHASTLY.form_id = 427
    PInstanceEvent.TIM_BIDOOF.form_id = 427
    PInstanceEvent.RATATA_4.form_id = 427

    # TODO ensure uniques of sharpedos form!!!
    PInstanceEvent.SHARPEDO.form_id = 435

    PInstanceEvent.BIDOOF_TOWER.form_id = PInstanceEvent.BIDOOF_8.form_id

    for event in PInstanceEvent.events():
        if event.m is None or event.form_id is None:
            continue
        # if event.m <= mission_goal:
        #     continue
        try:
            for i in event.i:
                place_npc(world, (event.map_name, i), event.form_id)
        except:
            print(event)
            raise

    apply_place_on_random(world, {"m001_006": [0]}, PInstanceEvent.NIGHT_PICHU.form_id)
    apply_place_on_random(world, {"m001_006": [1]}, PInstanceEvent.NIGHT_PICHU.form_id)

    for i in range(0, 4):
        apply_place_on_random(
            world, {"m001_011": [i]}, PInstanceEvent.NIGHT_GHASTLY.form_id
        )

    apply_place_on_random(world, {"m001_001": [5]}, PInstanceEvent.SLAKOTH.form_id)

    # if mission_goal <= 0:
    #     return
    apply_place_on_random(world, {"m006_001": [5]}, PInstanceEvent.CAVE_ZUBAT.form_id)
    # if mission_goal <= 2:
    #     return
    # if mission_goal <= 3:
    #     return
    # if mission_goal <= 4:
    #     return
    for i in [
        ("m011_001", 0),
        ("m011_002", 0),
        ("m011_004", 0),
    ]:
        place_npc(world, i, PInstanceEvent.SHARPEDO.form_id)
    apply_place_on_random(world, {"m011_005": [5]}, PInstanceEvent.SHARPEDO.form_id)

    # if mission_goal <= 5:
    #     return
    # if mission_goal <= 6:
    #     return
    # if mission_goal <= 7:
    #     return
    # if mission_goal <= 8:
    #     return
    # if mission_goal <= 9:
    #     return
    # if mission_goal <= 10:
    #     return
    # if mission_goal <= 11:
    #     return
    # if mission_goal <= 12:
    #     return
    # if mission_goal <= 15:
    #     return
    world.modified_script_mons |= {
        "NUZLEAF_2_1": PInstanceEvent.NUZLEAF_2.form_id,
        "NUZLEAF_2_2": PInstanceEvent.NUZLEAF_2.form_id,
        "UMBREON": PInstanceEvent.UMBREON.form_id,
        "BRONZONG": PInstanceEvent.BRONZONG.form_id,
        "SCEPTILE": PInstanceEvent.SCEPTILE.form_id,
        "LUXRAY": PInstanceEvent.LUXRAY.form_id,
    }


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

    print(len(party.items))

    for loc, item in zip(
        party.locations,
        party.items,
    ):
        loc.item = item

    party = world.capture_groups.capture_ocean
    for loc, item in zip(
        party.locations,
        party.items,
    ):
        loc.item = item

    # fill_restrictive(
    #     world.multiworld,
    #     state_default,
    #     locations=party.locations,
    #     item_pool=party.items,
    #     single_player_placement=True,
    #     swap=True,
    #     name="Randomize Pokémon - Default",
    # )
    #
    # if len(party.items) > 0:
    #     for loc, item in zip(
    #         party.locations,
    #         party.items,
    #     ):
    #         loc.item = item

    # party = world.capture_groups.capture_ocean
    # if len(party) > 0:
    #     state_ocean = CollectionState(world.multiworld)
    #     state_ocean.prog_items[world.player]["fill_restrictive"] = 1
    #     for item in my_progression_items:
    #         state_ocean.collect(item, True)
    #     fill_restrictive(
    #         world.multiworld,
    #         state_ocean,
    #         locations=party.locations,
    #         item_pool=party.items,
    #         single_player_placement=True,
    #         swap=True,
    #         name="Randomize Pokémon - Ocean",
    #     )

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
    world: PokemonRSOA, from_: str, to: str, mapping: Optional[Dict[int, int]] = None
) -> None:
    from_map = world.modified_regions[from_]
    if from_map.modified is False:
        return
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
    copy_over_map_pokemon(world, "m001_006", "m001_006", {1: 0})

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
    copy_over_map_pokemon(world, "m001_005", "m001_014", m001_005_to_m001_014)

    # #  rampardos
    # copy_over_spawn_to_npc(world, "m016_004", 2, "m016_004", 0)
    # copy_over_spawn_to_npc(world, "m016_004", 2, "m016_004", 1)

    # if world.modified_regions["m021_001"].modified:
    #     copy_over_spawn_to_npc(world, "m021_001", 14, "m021_001", 5)
    #     copy_over_spawn_to_npc(world, "m021_001", 14, "m021_001", 6)

    m029_001_to_m029_007 = {
        0: 1,
        1: 2,
        2: 4,
        3: 7,
        4: 6,
        5: 8,
    }
    copy_over_map_pokemon(world, "m029_001", "m029_007", m029_001_to_m029_007)

    m029_002_to_m029_008 = {
        0: 0,
        1: 1,
        2: 2,
        3: 3,  # NOT actually a match vanilla (but irrelevant if not randoized)
        4: 7,
        5: 5,
        6: 8,
    }
    copy_over_map_pokemon(world, "m029_002", "m029_008", m029_002_to_m029_008)

    copy_over_map_pokemon(world, "m039_003a", "m039_003b")
    copy_over_map_pokemon(world, "m039_005a", "m039_005b")
    copy_over_map_pokemon(world, "m039_007a", "m039_007b")

    """from here are purely cosmetic changes, which have npc mons matched to wild mons"""

    if world.modified_regions["m020_013"].modified:
        #  purugly and vulpix
        copy_over_spawn_to_npc(world, "m020_007", 2, "m019_002", 16)
        copy_over_spawn_to_npc(world, "m020_007", 2, "m018_004", 0)

        copy_over_spawn_to_npc(world, "m020_007", 1, "m019_002", 17)
        copy_over_spawn_to_npc(world, "m020_007", 1, "m018_004", 1)

        #  made the npcs somewhat the same as the mons that appear in the actual map,
        #  as these are the pokemon that should be running away in m8 cutscene
        #  doing it randomly however rather than setting the exact ones.

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

    if (
        world.options.randomize_pokemon != RandomizePokemonEncounters.option_vanilla
        and world.get_rule_num() >= 16
    ):
        for i in [1, 2, 3, 4]:
            j = world.random.randint(0, 16)
            copy_over_spawn_to_npc(world, "m021_001", j, "m021_001", i)

        #    for i in [1, 2, 3, 4]:
        #        j = world.random.randint(0, 17)
        #        copy_over_spawn_to_npc(world, "m010_022", j, "m010_022", i)
        ## not sure about these as these are likely also used for the wall!

        for i in [12, 13, 14, 15]:
            j = world.random.randint(0, 12)
            copy_over_spawn_to_npc(world, "m026_001", j, "m026_001", i)
        #  16 is abomasnow and is more npc, so changed with that setting

        # am i missing one???
        # for i in [12, 13, 14, 15]:
        #     j = world.random.randint(0, 13)
        #     copy_over_spawn_to_npc(world, "m026_001", j, "m026_001", i)

    return


def apply_randomize_npc_pokemon(world: PokemonRSOA) -> None:
    mission_goal = world.get_rule_num()
    groups: List[List[Tuple[str, int]]] = []

    if mission_goal >= 8:
        # consider making the drifloon groups the same???
        groups += [
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
        ]

        groups += [
            # --- partners
            [
                ("m020_006", 2),
                ("m020_009", 8),
                ("m001_014", 8),
            ],  # m8 barlow Makuhita
        ]
    #  skipped out on the Wendy Staraptor, as it's flying :c
    if mission_goal >= 9:
        groups += [
            [("m015_001", 11)],  # q12 budew
            [("m018_001", 22)],  # spinned around bidoof
        ]
        keith_buizel = [
            ("m017_004", 13),
        ]
        if mission_goal >= 14:
            keith_buizel += [
                ("m036_001", 0),
                ("m036_012", 1),
                ("m036_011", 2),
                ("m036_016", 5),
            ]
        groups += [
            # --- partners
            keith_buizel,
            [("m023_014", 12)],  # m9 sven Luxray
        ]
    if mission_goal >= 10:
        groups += [
            [("m026_001", 8), ("m025_001", 4), ("m025_002", 2)],  # cutscene empoleon
        ]
        #  consider copying the wild empoleon over the helped empoleon?
    if mission_goal >= 12:
        groups += [
            [
                ("m029_001", 1),
                ("m030_010", 7),
                ("m030_022", 1),
                ("m029_010", 2),
            ],  # m12 & m13 wailmer
        ]
    if mission_goal >= 14:
        groups += [
            [*[("m033_001", i) for i in range(13, 18)]],  # m14 hippopotas
        ]
    if mission_goal >= 16:
        groups += [
            [("m021_002", 4)],  # m16 girafarig
            [("m034_001", 4), ("m034_001", 5), ("m034_001", 6)],  # m16 more hippopotas
        ]

    pokemon = world.random.choices(
        [i for i in world.modified_species.keys() if i != 238], k=len(groups)
    )

    for group, mon in zip(groups, pokemon):
        form_id = list(world.modified_species[mon].forms.keys())[0]
        for place in group:
            place_npc(world, place, form_id)

    #  would randomize the abomasnow in the end cutscene, but crasehs game!
    # if world.get_rule_num() >= 16:
    #     mon = world.random.choice(pokemon)
    #     world.modified_npc_mon_to[156] = world.modified_species[mon].national_id
