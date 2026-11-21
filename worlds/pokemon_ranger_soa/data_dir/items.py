from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Tuple, Optional

from BaseClasses import ItemClassification


class ItemCategory(StrEnum):
    STYLER_UPGRADE = auto()
    PLAYER_ATTRIBUTES = auto()
    USEFUL = auto()
    FILLER = auto()
    UNIQUE = auto()
    PROGRESSIVE = auto()
    EVENT = auto()
    PARTNER = auto()
    FIELD_MOVE = auto()
    POWER_LEVEL = auto()
    TRAP = auto()


@dataclass()
class ItemData:
    label: str
    item_id: int
    classification: ItemClassification
    item_categories: Tuple[ItemCategory, ...]
    bit_offset: Optional[int] = None
    copies: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.classification, ItemClassification):
            self.classification = ItemClassification(self.classification)

        self.item_categories = tuple(
            c if isinstance(c, ItemCategory) else ItemCategory(c)
            for c in self.item_categories
        )


BASE_ITEMS = [
    # -------------- capture cards -----------------
    ItemData(
        label="Progressive Grass Defense",
        item_id=1,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=0,
        copies=2,
    ),
    ItemData(
        label="Progressive Water Defense",
        item_id=2,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=2,
        copies=2,
    ),
    ItemData(
        label="Progressive Electric Defense",
        item_id=3,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=4,
        copies=2,
    ),
    ItemData(
        label="Progressive Fire Defense",
        item_id=4,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=6,
        copies=2,
    ),
    ItemData(
        label="Progressive Fighting Defense",
        item_id=5,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=8,
        copies=2,
    ),
    ItemData(
        label="Progressive Poison Defense",
        item_id=6,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=10,
        copies=2,
    ),
    ItemData(
        label="Progressive Psychic Defense",
        item_id=7,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=12,
        copies=2,
    ),
    ItemData(
        label="Progressive Bug Defense",
        item_id=8,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=14,
        copies=2,
    ),
    ItemData(
        label="Progressive Ground Defense",
        item_id=9,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=16,
        copies=2,
    ),
    ItemData(
        label="Progressive Flying Defense",
        item_id=10,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=18,
        copies=2,
    ),
    ItemData(
        label="Progressive Dark Defense",
        item_id=11,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=20,
        copies=2,
    ),
    ItemData(
        label="Progressive Rock Defense",
        item_id=12,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=18,
        copies=2,
    ),
    ItemData(
        label="Progressive Ghost Defense",
        item_id=13,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=24,
        copies=2,
    ),
    ItemData(
        label="Progressive Ice Defense",
        item_id=14,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=26,
        copies=2,
    ),
    ItemData(
        label="Progressive Normal Defense",
        item_id=15,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=28,
        copies=2,
    ),
    ItemData(
        label="Progressive Steel Defense",
        item_id=16,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=30,
        copies=2,
    ),
    ItemData(
        label="Progressive Dragon Defense",
        item_id=17,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=32,
        copies=2,
    ),
    ItemData(
        label="Progressive Time Assist",
        item_id=18,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=34,
        copies=2,
    ),
    ItemData(
        label="Progressive Latent Power",
        item_id=19,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=36,
        copies=2,
    ),
    ItemData(
        label="Combo Bonus",
        item_id=20,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.UNIQUE),
        bit_offset=38,
        copies=1,
    ),
    ItemData(
        label="Progressive Recovery",
        item_id=21,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=40,
        copies=2,
    ),
    ItemData(
        label="Energy Plus",
        item_id=22,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.UNIQUE),
        bit_offset=42,
        copies=1,
    ),
    ItemData(
        label="Progressive Power Plus",
        item_id=23,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(
            ItemCategory.STYLER_UPGRADE,
            ItemCategory.PROGRESSIVE,
            ItemCategory.POWER_LEVEL,
        ),
        bit_offset=44,
        copies=2,
    ),
    ItemData(
        label="Progressive Long Line",
        item_id=24,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.PROGRESSIVE),
        bit_offset=46,
        copies=2,
    ),
    ItemData(
        label="Supreme Defense",
        item_id=25,
        classification=ItemClassification.useful | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.STYLER_UPGRADE, ItemCategory.UNIQUE),
        bit_offset=None,
        copies=1,
    ),
    # -------------- player attributes -----------------
    ItemData(
        label="Progressive Power",
        item_id=1001,
        classification=ItemClassification.progression
        | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.PLAYER_ATTRIBUTES),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Energy",
        item_id=1002,
        classification=ItemClassification.progression
        | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.PLAYER_ATTRIBUTES),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Level",
        item_id=1003,
        classification=ItemClassification.progression
        | ItemClassification.skip_balancing,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.PLAYER_ATTRIBUTES),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Styler",
        item_id=1004,
        classification=ItemClassification.useful,
        item_categories=(ItemCategory.PLAYER_ATTRIBUTES, ItemCategory.PROGRESSIVE),
        bit_offset=5,
        copies=2,
    ),
    ItemData(
        label="Progressive Rank",
        item_id=1005,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.PLAYER_ATTRIBUTES),
        bit_offset=None,
        copies=4,
    ),
    ItemData(
        label="Vatonage Styler",
        item_id=1006,
        classification=ItemClassification.filler,
        item_categories=(ItemCategory.PLAYER_ATTRIBUTES,),
        bit_offset=None,
        copies=1,
    ),
    # -------------- fieldmoves -----------------
    ItemData(
        label="Progressive Cut Unlock",
        item_id=10001,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Crush Unlock",
        item_id=10002,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Psy Power Unlock",
        item_id=10003,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Tackle Unlock",
        item_id=10004,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Electrify Unlock",
        item_id=10005,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Soak Unlock",
        item_id=10006,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Burn Unlock",
        item_id=10007,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Tunnel Unlock",
        item_id=10008,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive Recharge Unlock",
        item_id=10009,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Agility Unlock",
        item_id=10010,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Fly Unlock",
        item_id=10011,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Teleport Unlock",
        item_id=10012,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Rain Dance Unlock",
        item_id=10013,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Demist Unlock",
        item_id=10014,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Flash Unlock",
        item_id=10015,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Airlift Unlock",
        item_id=10016,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Elevate Unlock",
        item_id=10017,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Stink Unlock",
        item_id=10018,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Sand Fill Unlock",
        item_id=10019,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Progressive River Flow Unlock",
        item_id=10021,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Magma Flow Unlock",
        item_id=10022,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Swim Unlock",
        item_id=10023,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    ItemData(
        label="Dark Power Unlock",
        item_id=10024,
        classification=ItemClassification.progression,
        item_categories=(ItemCategory.PROGRESSIVE, ItemCategory.FIELD_MOVE),
        bit_offset=None,
    ),
    # -------------- traps -----------------
    ItemData(
        label="Gender Swap",
        item_id=15001,
        classification=ItemClassification.trap,
        item_categories=(ItemCategory.TRAP,),
        bit_offset=None,
        copies=1,
    ),
    # -------------- true filler -----------------
    ItemData(
        label="Woah. This is worthless!",
        item_id=100000,
        classification=ItemClassification.filler,
        item_categories=(ItemCategory.FILLER,),
        bit_offset=None,
        copies=1,
    ),
]
