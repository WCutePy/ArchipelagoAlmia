from __future__ import annotations
from typing import (
    TYPE_CHECKING,
)

from rule_builder.rules import Has, CanReachLocation, True_, CanReachRegion, HasFromListUnique
from . import options, data
from .data import determine_stage_location_count

if TYPE_CHECKING:
    from .world import PokemonTrozei


def set_all_rules(world: PokemonTrozei) -> None:

    for i, stage in enumerate(data.stages):

        try:

            for name in stage.get_location_names(determine_stage_location_count()):
                world.set_rule(
                    world.get_location(name),
                    Has(stage.unlock_name)
                )
        except:
            print(f"{i}, {stage} is not in this option set")


    # TODO change so this depends on the actual locations instead
     # to create a better spoiler log, the spoiler log currently does not consider
     # the actual level completion to goal, which is required for gameplay.
    stage = data.stages[35]
    required_bosses = world.options.required_bosses.value
    boss_unlock_items = (
        data.stages[30].unlock_name,
        data.stages[31].unlock_name,
        data.stages[32].unlock_name,
        data.stages[34].unlock_name,
        data.stages[33].unlock_name,
    )

    boss_30 = data.stages[30].unlock_name
    boss_32 = data.stages[32].unlock_name

    boss_rule = Has(stage.unlock_name) & Has(boss_30)
    if required_bosses == 2:
        boss_rule &= HasFromListUnique(
                *boss_unlock_items[0:4],
                count=required_bosses
            )
    elif required_bosses in [3, 4]:
        boss_rule &= (
            (HasFromListUnique(
                *boss_unlock_items,
                count=required_bosses
            ) & Has(boss_32)
             ) | HasFromListUnique(
                *boss_unlock_items[0:4],
                count=required_bosses
            )
        )
    else:
        boss_rule &= HasFromListUnique(
            *boss_unlock_items,
            count=required_bosses
            )

    for name in stage.get_location_names(determine_stage_location_count()):
        world.set_rule(
            world.get_location(name),
            boss_rule
        )

    world.set_rule(
        world.get_entrance("Map 2"),
        Has(data.stages[30].unlock_name)
    )
    world.set_rule(
        world.get_entrance("Map 3"),
        Has(data.stages[30].unlock_name)
    )
    world.set_rule(
        world.get_entrance("Map 4"),
        Has(data.stages[32].unlock_name) & Has(data.stages[30].unlock_name)
    )

    completion_condition = CanReachLocation(data.stages[35].location_names[0])
    world.set_completion_rule(completion_condition)
    return