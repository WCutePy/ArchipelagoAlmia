import pkgutil
from dataclasses import dataclass, field
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
    """TODO ORDER FOR DATA ORDER IN GAME"""

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
    """CORRECT ORDER"""

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

    @property
    def item_name(self) -> str:
        return f"Progressive {self.name.replace("_", " ").title()}"


class Party(StrEnum):
    DEFAULT = ""
    OCEAN = "_OCEAN"


@dataclass(frozen=True)
class FieldMove:
    category: FieldMoveCategory
    level: int

    def __post_init__(self):
        object.__setattr__(self, "category", FieldMoveCategory(self.category))

    def __str__(self):
        return f"{self.category.name}_{self.level}"

    def __lt__(self, other):
        if self.category == other.category:
            return self.level < other.level
        return self.category < other.category

    def satisfies(self, required: "FieldMove") -> bool:
        return self.category == required.category and self.level >= required.level

    def event_can_use_field_move_party(self, party: Party):
        return f"EVENT_USE_FIELD{party.value}-{self.category.name}-{self.level}"

    @classmethod
    def is_party(cls, string: str) -> Party:
        party, category_name, level_str = string[15:].split("-")
        return Party(party)

    @classmethod
    def from_string(cls, string: str) -> "FieldMove":
        party, category_name, level_str = string[15:].split("-")

        try:
            category = FieldMoveCategory[category_name]
        except KeyError as e:
            raise ValueError(f"Unknown FieldMoveCategory: {category_name}") from e

        try:
            level = int(level_str)
        except ValueError as e:
            raise ValueError(f"Invalid level: {level_str}") from e

        return cls(category=category, level=level)


@dataclass
class FormData:
    hex_form_id: str
    friendship_gauge: int


@dataclass
class SpeciesData:
    name: str
    label: str

    browser_id: int
    national_id: int
    forms: Dict[int, FormData]

    field_move: FieldMove
    poke_assist: PokeAssistCategory

    browser_offset: int
    browser_flag: int

    browser_rank_offset: Optional[int] = None
    browser_rank_flag: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.field_move, dict):
            self.field_move = FieldMove(**self.field_move)

        self.forms = {
            int(form_id): (form if isinstance(form, FormData) else FormData(**form))
            for form_id, form in self.forms.items()
        }

    @property
    def location_capture_name(self):
        return f"CAPTURE_{self.name}"

    def event_missable(self, form: Optional[int] = None):
        return f"EVENT_MISSABLE;{self.name}"

    def event_add_to_browser(self, form: Optional[int] = None):
        return f"EVENT_ADD_TO_BROWSER;{self.name}"

    def event_can_capture(
        self, party: Party = Party.DEFAULT, form: Optional[int] = None
    ):
        return f"EVENT_CAN_CAPTURE{party.value};{self.name}"

    @property
    def location_capture_rank_name(self):
        return f"CAPTURE_RANK_{self.name}"


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


@dataclass()
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


@dataclass
class TargetEntry:
    TARGET_ID: int
    TARGET_NAME: str


@dataclass
class PokemonSpawnEntry:
    SPECIES_ID: int  # form_id
    SPECIES_NAME: str
    SPAWN_FLAG: int
    missable: Optional[bool] = False
    one_time: Optional[bool] = False
    randomize: Optional[bool] = True
    browser_before_capture: Optional[bool] = False
    rules: list[str] = field(default_factory=list)

    def set_form(self, form_id: int):
        self.SPECIES_ID = form_id
        self.SPECIES_NAME = data.form_id_to_species[form_id].name


@dataclass
class NPCEntry:
    unk1: int
    unk2: int
    unk3: int
    script_id: int = -1
    NAME: str = "UNK"
    randomize: Optional[bool] = False


@dataclass
class MapData:
    map_id: str

    INDEX: str
    HUMAN_NAME: str

    TARGETS: dict[int, TargetEntry] = field(default_factory=dict)
    POKEMON_SPAWN: dict[int, PokemonSpawnEntry] = field(default_factory=dict)
    NPCS: dict[int, NPCEntry] = field(default_factory=dict)
    EXITS: dict[str, list[str]] = field(default_factory=dict)

    modified: Optional[bool] = False

    def __post_init__(self):
        self.TARGETS = {
            int(key): (
                value if isinstance(value, TargetEntry) else TargetEntry(**value)
            )
            for key, value in self.TARGETS.items()
        }

        if self.NPCS:
            self.NPCS = {
                int(key): (value if isinstance(value, NPCEntry) else NPCEntry(**value))
                for key, value in self.NPCS.items()
            }

        self.POKEMON_SPAWN = {
            int(key): (
                value
                if isinstance(value, PokemonSpawnEntry)
                else PokemonSpawnEntry(
                    **{
                        **value,
                        "SPECIES_ID": (
                            int(value["SPECIES_ID"], 16)
                            if isinstance(value.get("SPECIES_ID"), str)
                            else value["SPECIES_ID"]
                        ),
                    }
                )
            )
            for key, value in self.POKEMON_SPAWN.items()
        }


class PokemonRSOAData:
    species: Dict[
        int, SpeciesData
    ]  # browser id - SpeciesData, duplicate forms are stored under the same browser id
    form_id_to_species: Dict[int, SpeciesData]
    regions: Dict[str, MapData]  # m001_001 - MapData
    map_id_to_region_name: Dict[int, str]
    locations: Dict[str, LocationData]
    items: Dict[int, ItemData]

    styler_levels: List[Tuple[int, int]]  # each entry is a level with Energy, Power
    target_field_move_requirements: Dict[int, FieldMove]

    ram_addresses: Dict[str, AddressesGroup]
    rom_addresses: Dict[str, AddressesGroup]

    def __init__(self) -> None:
        self.species = {}
        self.form_id_to_species = {}
        self.regions = {}
        self.map_id_to_region_name = {}
        self.locations = {}
        self.items = {}
        self.ram_addresses = {}
        self.rom_addresses = {}
        self.styler_levels = []
        self.target_field_move_requirements = {}


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


def sanitize_map_name(map_name: Union[str, int]) -> str:
    if isinstance(map_name, int):
        map_name = data.map_id_to_region_name[map_name]
    elif map_name.lower().startswith("0x"):
        map_name = data.map_id_to_region_name[int(map_name, 16)]
    return map_name


def pokemon_to_target_id(name: str) -> Optional[int]:
    name = name.lower()
    mapping = {
        "oddish": 0x1,
        "gloom": 0x2,
        "vileplume": 0x3,
        "geodude": 0x4,
        "graveler": 0x5,
        "sudowoodo": 0x6,
        "cacturne": 0x7,
        # "claydol": 0x8,
        "torterra": 0x9,
        "bronzor": 0xA,
        "bonsly": 0xB,
        "carnivine": 0xC,
        "abomasnow": 0xD,
    }
    return mapping.get(name, None)


def _init():

    extracted_species: List[Dict] = load_json_data("species.json")

    for species_data in extracted_species:
        species = SpeciesData(**species_data)
        data.species[species.browser_id] = species
        for form in species.forms.keys():
            data.form_id_to_species[form] = species

    extracted_items: List[Dict] = load_json_data("items.json")

    for i, item_data in enumerate(extracted_items):
        try:
            item = ItemData(**item_data)
        except:
            print("errored loading item: ")
            print(item_data)
            raise
        data.items[item.item_id] = item

    extracted_regions: List[Dict] = load_json_data("regions.json")

    region_data_fields = ["TRIGGERS"]
    for i, region_data in extracted_regions.items():
        filtered_data = {
            k: v for k, v in region_data.items() if k not in region_data_fields
        }

        region = MapData(
            map_id=i,
            **filtered_data,
        )

        data.regions[i] = region
        data.map_id_to_region_name[int(region_data["INDEX"], 16)] = i

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

    CATEGORY_TO_ATTR = {
        LocationCategory.BROWSER: "location_capture_name",
        LocationCategory.BROWSER_RANK: "location_capture_rank_name",
    }
    for category, str_attr in CATEGORY_TO_ATTR.items():
        for browser_id, species_data in data.species.items():

            id = location_category_to_id(browser_id, category)

            name = getattr(species_data, str_attr)
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

    target_requirements = load_json_data("target_field_move_requirements.json")
    for i, requirements in target_requirements.items():
        data.target_field_move_requirements[int(i)] = FieldMove(
            **requirements,
        )


try:
    data
except NameError:
    data = PokemonRSOAData()
    _init()
