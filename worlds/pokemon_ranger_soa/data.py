import pkgutil
from dataclasses import dataclass
from enum import IntEnum
from typing import NamedTuple, Union, List, FrozenSet, Dict, Any, Optional

import re
import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import unicodedata
from orjson import orjson

from BaseClasses import ItemClassification

BASE_OFFSET = 1000

BROWSER_START_ADDRESS = 0x020BA2DD
BROWSER_RANK_START_ADDRESS = 0x020BA551


class LocationCategory(IntEnum):
    BROWSER = 1
    BROWSER_RANK = 2
    MISSION = 3
    QUEST = 4


class LocationData(NamedTuple):
    name: str
    label: str
    parent_region: str
    default_item: int
    address: Union[int, List[int]]
    flag: int
    category: LocationCategory
    tags: FrozenSet[str]


class PokeAssistCategory(IntEnum):
    NONE = 0
    GRASS = 1
    FLYING = 2
    NORMAL = 3
    RECHARGE = 4
    WATER = 5
    ROCK = 6
    ELECTRIC = 7
    BUG = 8
    FIRE = 9
    FIGHTING = 10
    GROUND = 11
    STEEL = 12
    POISON = 13
    GHOST = 14
    PSYCHIC = 15
    DARK = 16
    ICE = 17
    DRAGON = 18


class FieldMoveCategory(IntEnum):
    NONE = 0
    BURN = 1
    CRUSH = 2
    CUT = 3
    ELECTRIFY = 4
    PSY_POWER = 5
    SOAK = 6
    TUNNEL = 7
    TACKLE = 8
    AGILITY = 9
    FLY = 10
    RECHARGE = 11
    TELEPORT = 12
    AIRLIFT = 13
    DARK_POWER = 14
    DEMIST = 15
    ELEVATE = 16
    FLASH = 17
    MAGMA_FLOW = 18
    RAIN_DANCE = 19
    SAND_FILL = 20
    STINK = 21
    SWIM = 22
    RIVER_FLOW = 23


@dataclass(frozen=True)
class FieldMove:
    category: FieldMoveCategory
    level: int

    def satisfies(self, required: "FieldMove") -> bool:
        return self.category == required.category and self.level >= required.level

    @classmethod
    def from_string(cls, string: str) -> "FieldMove":
        raise NotImplemented


@dataclass
class SpeciesData:
    name: str
    label: str
    browser_id: int
    species_ids: List[int]
    hex_ids: List[str]
    field_move: FieldMove
    poke_assist: PokeAssistCategory
    friendship_gauge: tuple[int]

    browser_flag_address: int
    browser_flag: int
    browser_rank_flag_address: Optional[int] = None
    browser_rank_flag: Optional[int] = None

    @property
    def browser_offset(self) -> int:
        return self.browser_flag_address - BROWSER_START_ADDRESS


@dataclass
class MapData:
    name: str
    label: str


class EventData(NamedTuple):
    name: str
    parent_region: str


class RegionData:
    name: str
    exits: List[str]
    locations: List[str]
    events: List[EventData]

    def __init__(self, name: str):
        self.name = name
        self.exits = []
        self.locations = []
        self.events = []


class ItemData(NamedTuple):
    label: str
    item_id: int
    classification: ItemClassification
    tags: FrozenSet[str]


class PokemonRSOAData:
    species: Dict[int, SpeciesData]
    locations: Dict[str, LocationData]
    items: Dict[int, ItemData]

    def __init__(self) -> None:
        self.species = {}
        self.locations = {}
        self.items = {}


def load_json_data(data_name: str) -> Union[List[Any], Dict[str, Any]]:
    return orjson.loads(
        pkgutil.get_data(__name__, "data/" + data_name).decode("utf-8-sig")
    )


def _init():

    extracted_species: List[Dict] = load_json_data("species.json")

    for species_data in extracted_species:
        species = SpeciesData(**species_data)
        data.species[species.browser_id] = species

    styler_power_ups = [
        "Normal Defense 1",
        "Normal Defense 2",
        "Fire Defense 1",
        "Fire Defense 2",
        "Water Defense 1",
        "Water Defense 2",
        "Electric Defense 1",
        "Electric Defense 2",
        "Grass Defense 1",
        "Grass Defense 2",
        "Ice Defense 1",
        "Ice Defense 2",
        "Fighting Defense 1",
        "Fighting Defense 2",
        "Poison Defense 1",
        "Poison Defense 2",
        "Ground Defense 1",
        "Ground Defense 2",
        "Flying Defense 1",
        "Flying Defense 2",
        "Psychic Defense 1",
        "Psychic Defense 2",
        "Bug Defense 1",
        "Bug Defense 2",
        "Rock Defense 1",
        "Rock Defense 2",
        "Ghost Defense 1",
        "Ghost Defense 2",
        "Dragon Defense 1",
        "Dragon Defense 2",
        "Dark Defense 1",
        "Dark Defense 2",
        "Steel Defense 1",
        "Steel Defense 2",
        "Supreme Defense 1",
        "Time Assist 1",
        "Time Assist 2",
        "Latent Power 1",
        "Latent Power 2",
        "Recovery 1",
        "Recovery 2",
        "Combo Bonus 1",
        "Long Line 1",
        "Long Line 2",
        "Power Plus 1",
        "Power Plus 2",
        "Energy Plus 1",
    ]

    for i, power_up in enumerate(styler_power_ups):
        item = ItemData(power_up, i, ItemClassification.progression, frozenset())

        data.items[i] = item

    data.items[10000] = ItemData(
        "Filler Item", 10000, ItemClassification.useful, frozenset()
    )


data = PokemonRSOAData()

_init()
