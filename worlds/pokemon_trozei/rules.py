from __future__ import annotations
from typing import (
    TYPE_CHECKING,
)

from rule_builder.rules import Has, CanReachLocation
from . import options, data
from .data import determine_stage_location_count

if TYPE_CHECKING:
    from .world import PokemonTrozei


def set_all_rules(world: PokemonTrozei) -> None:

    for i in [0, 5, 1, 2, 6, 7, 30]:
        stage = data.stages[i]
        location_names = []

        for name in stage.get_location_names(determine_stage_location_count()):
            world.set_rule(
                world.get_location(name),
                Has(stage.unlock_name)
            )


    completion_condition = CanReachLocation(data.stages[30].location_names[0])
    world.set_completion_rule(completion_condition)
    return