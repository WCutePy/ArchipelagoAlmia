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
POKE_ID_ROW_ROM_SIZE = 28
POKE_ID_ROW_RAM_SIZE = 24


class GameStateEnum(IntEnum):
    OVERWORLD = 0x00
    BATTLE = 0x01
    BLACK_SCREEN = 0x02
    MISSION_SCREEN = 0x08
    ...


class LocationCategory(StrEnum):
    BROWSER = auto()
    BROWSER_RANK = auto()
    MISSION = auto()
    QUEST = auto()


@dataclass
class LocationData:
    name: str
    label: str
    parent_region: Optional[str]
    default_item: Optional[int]
    addresses: Optional[List[str]]
    flag: Optional[int]
    category: LocationCategory
    id: Optional[int]

    def __post_init__(self):
        if not isinstance(self.category, LocationCategory):
            self.category = LocationCategory(self.category)


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
    CUT = 1
    CRUSH = 2
    PSY_POWER = 3
    TACKLE = 4
    ELECTRIFY = 5
    SOAK = 6
    BURN = 7
    TUNNEL = 8
    RECHARGE = 9
    AGILITY = 10
    FLY = 11
    TELEPORT = 12
    RAIN_DANCE = 13
    DEMIST = 14
    FLASH = 15
    AIRLIFT = 16
    ELEVATE = 17
    STINK = 18
    SAND_FILL = 19
    AURA_BLAST = 20
    RIVER_FLOW = 21
    MAGMA_FLOW = 22
    SWIM = 23
    DARK_POWER = 24


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
    national_id: int
    form_ids: List[int]
    hex_form_ids: List[str]
    poke_id_indexes: List[int]

    field_move: FieldMove
    poke_assist: PokeAssistCategory
    friendship_gauge: tuple[int]

    browser_offset: int
    browser_flag: int

    browser_rank_offset: Optional[int] = None
    browser_rank_flag: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.field_move, dict):
            self.field_move = FieldMove(**self.field_move)


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
    PARTNER = auto()
    FIELD_MOVE = auto()


class AddressesGroup(NamedTuple):
    addresses: list[int]
    label: str
    bit_length: Optional[int] = None
    descriptor: Optional[str] = None

    @property
    def first(self):
        return self.addresses[0]

    @classmethod
    def create_from_dict(cls, info: dict):
        addresses_as_int = [
            int(num, 16) if isinstance(num, str) else num for num in info.get("address")
        ]

        return AddressesGroup(
            addresses=addresses_as_int,
            bit_length=info.get("bit_offset"),
            label=info.get("label"),
            descriptor=info.get("descriptor"),
        )


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
    species: Dict[
        int, SpeciesData
    ]  # browser id - SpeciesData, duplicate forms have duplicate ids.
    locations: Dict[str, LocationData]
    items: Dict[int, ItemData]
    styler_levels: List[Tuple[int, int]]  # each entry is a level with Energy, Power

    ram_addresses: Dict[str, AddressesGroup]
    rom_addresses: Dict[str, AddressesGroup]

    def __init__(self) -> None:
        self.species = {}
        self.locations = {}
        self.items = {}
        self.ram_addresses = {}
        self.rom_addresses = {}
        self.styler_levels = []


def load_json_data(data_name: str) -> Union[List[Any], Dict[str, Any]]:
    return orjson.loads(
        pkgutil.get_data(__name__, "data/" + data_name).decode("utf-8-sig")
    )


def location_category_to_id(base_number: int, category: str):
    if category == LocationCategory.MISSION:
        return base_number + 1
    if category == LocationCategory.QUEST:
        return base_number + 100
    if category == LocationCategory.BROWSER:
        return base_number + 1000
    if category == LocationCategory.BROWSER_RANK:
        return base_number + 10000
    raise ValueError(category)


def _init():

    extracted_species: List[Dict] = load_json_data("species.json")

    for species_data in extracted_species:
        species = SpeciesData(**species_data)
        data.species[species.browser_id] = species

    extracted_items: List[Dict] = load_json_data("items.json")

    for i, item_data in enumerate(extracted_items):
        try:
            item = ItemData(**item_data)
        except:
            print("errored loading item: ")
            print(item_data)
            raise
        data.items[item.item_id] = item

    extracted_locations: Dict[str, Dict] = load_json_data("locations.json")

    counter = 0
    for name, location_data in extracted_locations.items():
        counter += 1
        try:
            prefix, number = name.split("_")
            number = location_category_to_id(int(number), location_data["category"])
        except ValueError:
            number = None
            print(f"error generating a number for: {name}, {location_data}")

        if isinstance(location_data["addresses"], str):
            location_data["addresses"] = [location_data["addresses"]]

        data.locations[name] = LocationData(name=name, id=number, **location_data)

    for string in ["Capture {}", "Capture {} Rank"]:
        if string == "Capture {}":
            category = LocationCategory.BROWSER
        if string == "Capture {} Rank":
            category = LocationCategory.BROWSER_RANK
        for browser_id, species_data in data.species.items():

            id = location_category_to_id(browser_id, category)

            name = string.format(species_data.name)
            location = LocationData(
                name=name,
                label=name,
                parent_region=None,
                default_item=None,
                addresses=None,
                flag=None,
                category=category,
                id=id,
            )
            data.locations[name] = location

    ram_addresses = load_json_data("addresses_ram.json")
    for entry in ram_addresses:
        r = AddressesGroup.create_from_dict(entry)
        data.ram_addresses[r.label] = r

    rom_addresses = load_json_data("addresses_rom.json")
    for entry in rom_addresses:
        r = AddressesGroup.create_from_dict(entry)
        data.rom_addresses[r.label] = r

    styler_levels = load_json_data("styler_level.json")
    for i, level in enumerate(styler_levels, start=1):
        if i == 100:
            break
        data.styler_levels.append(tuple(level))


data = PokemonRSOAData()

_init()
