from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Dict,
    Union,
    Optional,
    List,
    TypeAlias,
    Iterable,
    Sized,
    ClassVar,
    Any,
)
from collections import defaultdict
from dataclasses import field, dataclass
from rule_builder.rules import (
    Has,
    Rule,
    HasAllCounts,
    True_,
    CanReachLocation,
    CanReachRegion,
    False_,
    HasFromList,
    HasFromListUnique,
)

from .data import (
    data,
    ItemCategory,
    FieldMove,
    LocationCategory,
    pokemon_to_target_id,
    FieldMoveCategory,
    MapData,
)
from .events import (
    PREvent,
    get_instance_base,
    get_instance_capture,
    get_instance_target,
    get_loading_zone_name,
    get_instance_browser,
    PInstanceEvent,
    get_mission_event,
    get_quest_event,
    get_instance_missable,
)
from .options import FieldMoveItem, Goal

if TYPE_CHECKING:
    from .world import PokemonRSOA

"""
TODO, create randomizer functions,
for now a non exhaustive list of potential script moved/spawned pokémon.

school tutorial:
 - running bidoof (might not be on the map)
 - 4 ghastly basement (on map!
 - slakoth from tree (likely on map)
 - tangrowth during graduation (not on map)

nabiki beach
 - starter partners

mission 2 marine cave
 - entrance zubat attacking you (on map)
 - circle running (on map)

quest 1
 - milktank

mission 3
 - 4 budew that jump out
 - maybe happiny related
"""


def sanitize_map_name(map_name: Union[str, int]) -> str:
    if isinstance(map_name, int):
        map_name = data.map_id_to_region_name[map_name]
    elif map_name.lower().startswith("0x"):
        map_name = data.map_id_to_region_name[int(map_name, 16)]
    return map_name


@dataclass
class MonSelect:
    world: ClassVar[Optional[PokemonRSOA]]
    include: Dict[str, List] = field(default_factory=dict)
    exclude: Dict[str, List] = field(default_factory=dict)
    event_mon: List[PInstanceEvent] = field(default_factory=list)

    include_one_time: bool = False
    include_missable: bool = False

    def region_included(
        self, region_name: str, region_data: Optional[MapData] = None
    ) -> bool:
        """
        If the map should be excluded for the current set
        of includes and excludes.
        """
        if region_data:
            blacklisted = any(
                w in region_data.HUMAN_NAME
                for w in [
                    "DLC",
                    "-UNK",
                    "-UNUSED",
                    "ALTRU_TOWER-SKY-BLUE",
                    "ALTRU_TOWER-6F_ROOF-DARK_CRYSTAL_DARK_CLOUDS_2",
                    "VIENTOWN-RANGER_STATION_BACKROOM",
                    "OIL_FIELD_HIDEOUT-B2_WEST_HALLWAY-DARK",
                ]
                if not (w == "-UNK" and "m009" in region_name)
            )
            if blacklisted:
                return False

        if self.exclude and (
            len(self.exclude.get(region_name, [1])) == 0
            or any(
                region_name.startswith(e.lower())
                for e in self.exclude
                if "_" not in e and not self.exclude.get(region_name, [])
            )
        ):
            return False

        include_region: bool = next(
            (
                self.include[i]
                for i in self.include
                if region_name.startswith(i.lower())
            ),
            False,
        )
        if self.include and include_region is False:
            return False
        return True

    def instance_included(
        self, region_name: str, i: int, instance_type: Optional[str] = "pokemon"
    ) -> bool:

        if self.exclude and i in self.exclude.get(region_name, []):
            return False

        if self.include:
            base_region = region_name.split("_")[0].lower()
            if base_region in self.include:
                return True

            include_region = self.include.get(region_name, [-1])
            if len(include_region) > 0 and i not in include_region:
                return False

        return True

    def event_mon_included(self, event: PInstanceEvent):

        return True

    def access_field_move(
        self,
        field_move: FieldMove,
    ) -> Rule:
        pokemon_rules = False_()
        for region_name, region_data in self.world.modified_regions.items():
            region_name = region_name.lower()

            if not self.region_included(region_name, region_data):
                continue
            include_region: Sized

            for i, spawn_data in region_data.POKEMON_SPAWN.items():

                if not self.instance_included(region_name, i):
                    continue

                if not self.include_missable and spawn_data.missable:
                    continue
                if not self.include_one_time and spawn_data.one_time:
                    continue

                species = data.form_id_to_species[spawn_data.SPECIES_ID]
                if species.field_move.satisfies(field_move):
                    if self.include_missable and spawn_data.missable:
                        pokemon_rules |= CanReachLocation(
                            get_instance_missable(region_name, i)
                        )
                    elif self.include_one_time and spawn_data.one_time:
                        pokemon_rules |= CanReachLocation(
                            get_instance_browser(region_name, i)
                        )
                    else:
                        pokemon_rules |= CanReachLocation(
                            get_instance_capture(region_name, i)
                        )

        return pokemon_rules

    def can_destroy_target(
        self,
        map_name: Union[str, int],
        i: int,
        on_self: bool = False,
    ) -> Rule:
        """
        TODO, reconsider if it's necessary to have a field move restriction to target events
        and instead handle it here fully, for now leaving as is, some minor duplication of
        logic is here right now, as being able to use field move item is inhernt from
        Has(target)

        MUST be exhausted directly, as include and exclude are expected to be expanded over
        its use
        """
        map_name = sanitize_map_name(map_name)
        target = get_instance_target(map_name, i)

        field_move = data.target_field_move_requirements[
            self.world.modified_regions[map_name].TARGETS[i].TARGET_ID
        ]

        if not self.include and not self.exclude:
            base = Has(field_move.event_can_use_field_move)
            # if not on_self:
            #     base &= Has(target)
            return base

        return has_field_move_item(self.world, field_move) & self.access_field_move(
            field_move
        )

    def can_destroy_target_type(
        self,
        target_id: int,
    ) -> Rule:
        """
        The int of the target

        any len 0 iterable in MonSelect evaluates to the whole map.
        any len >=1 iterable accounts only the specified members in the iterable
        """
        field_move: FieldMove = data.target_field_move_requirements[target_id]

        if not self.include and not self.exclude:
            return Has(field_move.event_can_use_field_move)

        return has_field_move_item(self.world, field_move) & self.access_field_move(
            field_move
        )

    def can_use_field_move(self, field_move: FieldMove) -> Rule:
        if not self.include and not self.exclude:
            return Has(field_move.event_can_use_field_move)

        return has_field_move_item(self.world, field_move) & self.access_field_move(
            field_move
        )

    @classmethod
    def full_map(cls) -> MonSelect:
        return MonSelect()

    @classmethod
    def tutorial_school_area(cls) -> MonSelect:
        #  TODO, add ship area to include when randomizing
        return MonSelect(
            include={
                "m001_002": [],
                "m001_003a": [],  # quite sure all are available
                "m001_005": [],
                "m001_009": [],
                "m001_011": [],
                "m001_001": [0, 1, 2, 5],
                "m001_015": [],
            },
        )

    @classmethod
    def marine_cave(cls) -> MonSelect:
        """Technically identical to outside_school_before_return_school,
        but semantically preferred to strictly specify on such
        small sample size"""
        return MonSelect(
            include={
                "m001_001": [3, 4],
                "m005_001b": [],
                "m007_001": [],
                "m006_002": [],  # unreachable until a bit later
                "m006_003": [],  # unreachable until a bit later
                "m006_004": [],  # unreachable until a bit later
            },
        )

    @classmethod
    def get_rules_scope(cls) -> MonSelect:
        """
        Go through the rules to determine the currently
        applicable MonSelect instance
        """
        goals = {
            0: cls.goal_school,
            2: cls.goal_marine_cave,
        }

        if cls.world.options.goal == Goal.option_mission_clear:

            return goals[cls.world.options.mission_clear_target.value]()

    @classmethod
    def goal_school(cls) -> MonSelect:
        """
        Goal: capture cutscene Tangrowth

        Possibly reachable instances:

        missions: 1
        quests: 0
        Missable_pokemon: 17
        Unique Browser Captures: 34
        Browser Instances: 1
        Capture Instances: 33

        if ship is included
        missable_locations:
        browser_locations:
        capture_locations:
        """

        return MonSelect(
            include={"m001": [], "m003": [], "m007": []},
            exclude={
                "m001_001": [2],
                "m001_002": [6, 12],
                "m001_014": [],
                "m001_011": [5],
                "m003_001": [0, 3],
                "m007_001": [0, 2],
            },
            event_mon=[PInstanceEvent.TANGROWTH],
        )

    @classmethod
    def goal_marine_cave(cls) -> MonSelect:
        """

        Unique Browser Captures: 57
        Browser Instances: 1
        Capture Instances: 56
        """
        base = cls.goal_school()
        base.include |= {
            "m005_001b": [],
            "m006": [],
        }
        return base

    @classmethod
    def goal_forest_fire(cls) -> MonSelect:
        base = cls.goal_marine_cave()
        base.include |= {
            "m009_002": [],
            "m009_001a": [],
            "m009_009": [],
            "m009_004": [8],
        }
        base.exclude |= {"m009_009": [2, 3]}

        base.event_mon += [PInstanceEvent.MILTANK]


def has_field_move_item(world: PokemonRSOA, field_move: FieldMove) -> Rule:
    if world.options.field_move_item == FieldMoveItem.option_vanilla:
        return True_()

    return Has(
        field_move.category.item_name,
        1,
    )
