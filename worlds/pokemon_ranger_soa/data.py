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


class PokemonRSOAData:
    species: Dict[int, SpeciesData]
    locations: Dict[str, LocationData]
    items: Dict[int, ItemData]

    ram_addresses: Dict[str, RamAddress]

    def __init__(self) -> None:
        self.species = {}
        self.locations = {}
        self.items = {}
        self.ram_addresses = {}


def load_json_data(data_name: str) -> Union[List[Any], Dict[str, Any]]:
    return orjson.loads(
        pkgutil.get_data(__name__, "data/" + data_name).decode("utf-8-sig")
    )


def _init():

    extracted_species: List[Dict] = load_json_data("species.json")

    for species_data in extracted_species:
        species = SpeciesData(**species_data)
        data.species[species.browser_id] = species

    STYLER_UPGRADES = (
        ("Progressive Grass Defense", 2, 0),
        ("Progressive Water Defense", 2, 2),
        ("Progressive Electric Defense", 2, 4),
        ("Progressive Fire Defense", 2, 6),
        ("Progressive Fighting Defense", 2, 8),
        ("Progressive Poison Defense", 2, 10),
        ("Progressive Psychic Defense", 2, 12),
        ("Progressive Bug Defense", 2, 14),
        ("Progressive Ground Defense", 2, 16),
        ("Progressive Flying Defense", 2, 18),
        ("Progressive Dark Defense", 2, 20),
        ("Progressive Rock Defense", 2, 18),
        ("Progressive Ghost Defense", 2, 24),
        ("Progressive Ice Defense", 2, 26),
        ("Progressive Normal Defense", 2, 28),
        ("Progressive Steel Defense", 2, 30),
        ("Progressive Dragon Defense", 2, 32),
        ("Progressive Time Assist", 2, 34),
        ("Progressive Latent Power", 2, 36),
        ("Combo Bonus", 1, 38),  # Bit 31 also toggles it on.
        ("Progressive Recovery", 2, 40),
        ("Energy Plus", 1, 42),  # Bit 35 also toggles it on.
        ("Progressive Power Plus", 2, 44),
        ("Progressive Long Line", 2, 46),
        #
        (
            "Supreme Defense",
            1,
            None,
        ),  # Dragon Defense both bits turned on will indicate Supreme Defense.
        # This does however not impact the others.
    )

    for i, (power_up, count, bit) in enumerate(STYLER_UPGRADES):
        item = ItemData(
            power_up,
            i,
            ItemClassification.progression,
            (
                ItemCategory.STYLER_UPGRADE,
                ItemCategory.UNIQUE if count == 1 else ItemCategory.PROGRESSIVE,
            ),
            bit,
            copies=count,
        )

        data.items[i] = item

    data.items[10000] = ItemData(
        "Filler Item", 10000, ItemClassification.useful, (ItemCategory.FILLER,)
    )

    r = RamAddress(0x020BA302, 24, "RECEIVED_ITEM_ADDRESS")
    data.ram_addresses[r.label] = r

    r = RamAddress(0x020BAE7C, None, "STYLUS_UPGRADE_TABLE_ADDRESS")
    data.ram_addresses[r.label] = r


data = PokemonRSOAData()

_init()
