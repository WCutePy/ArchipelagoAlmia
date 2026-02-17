import pkgutil
from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto
from typing import NamedTuple, Union, List, FrozenSet, Dict, Any, Optional, Tuple

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


class GameStateEnum(IntEnum):
    OVERWORLD = 0x00
    BATTLE = 0x01
    BLACK_SCREEN = 0x02
    MISSION_SCREEN = 0x08
    ...


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

    browser_offset: int
    browser_flag: int
    browser_rank_offset: Optional[int] = None
    browser_rank_flag: Optional[int] = None


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


class ItemCategory(StrEnum):
    STYLER_UPGRADE = auto()
    PLAYER_ATTRIBUTES = auto()
    FILLER = auto()
    UNIQUE = auto()
    PROGRESSIVE = auto()
    EVENT = auto()


class RamAddress(NamedTuple):
    address: int
    bit_length: Optional[int] = None
    label: Optional[str] = None


@dataclass
class ItemData:
    label: str
    item_id: int
    classification: ItemClassification
    item_categories: Tuple[ItemCategory, ...]
    bit_offset: Optional[int] = None
    copies: int = 1

    def __post_init__(self):
        if not isinstance(self.classification, ItemClassification):
            self.classification = ItemClassification(self.classification)

        self.item_categories = tuple(
            c if isinstance(c, ItemCategory) else ItemCategory(c)
            for c in self.item_categories
        )


class PokemonRSOAData:
    species: Dict[int, SpeciesData]
    locations: Dict[str, LocationData]
    items: Dict[int, ItemData]
    styler_levels: List[Tuple[int, int]]  # each entry is a level with Energy, Power

    ram_addresses: Dict[str, RamAddress]

    def __init__(self) -> None:
        self.species = {}
        self.locations = {}
        self.items = {}
        self.ram_addresses = {}
        self.styler_levels = []


def load_json_data(data_name: str) -> Union[List[Any], Dict[str, Any]]:
    return orjson.loads(
        pkgutil.get_data(__name__, "data/" + data_name).decode("utf-8-sig")
    )


def _init():

    extracted_species: List[Dict] = load_json_data("species.json")

    for species_data in extracted_species:
        species = SpeciesData(**species_data)
        data.species[species.browser_id] = species

    extracted_items: List[Dict] = load_json_data("items.json")

    for i, item_data in enumerate(extracted_items):
        item = ItemData(**item_data)

        data.items[item.item_id] = item

    ram_addresses = load_json_data("addresses.json")
    for entry in ram_addresses:
        address_int = (
            int(entry.get("address"), 16)
            if isinstance(entry.get("address"), str)
            else entry.get("address")
        )

        r = RamAddress(
            address=address_int,
            bit_length=entry.get("bit_offset"),
            label=entry.get("label"),
        )
        data.ram_addresses[r.label] = r

    styler_levels = load_json_data("styler_level.json")
    for i, level in enumerate(styler_levels, start=1):
        if i == 100:
            break
        data.styler_levels.append(tuple(level))


data = PokemonRSOAData()

_init()
