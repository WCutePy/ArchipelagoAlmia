from dataclasses import dataclass
from enum import Enum
from typing import Optional


def get_instance_target(map_name: str, index: int) -> str:
    """target instance location and item name"""
    return f"{map_name}.T.{index}"


def get_instance_base(map_name: str, index: int) -> str:
    """instance region name and connection name"""
    return f"{map_name}.P.{index}"


def get_instance_browser(instance: str, index: Optional[int] = None) -> str:
    """instance browser location name"""
    if index is not None:
        instance = get_instance_base(instance, index)
    return f"{instance}_browser"


def get_instance_missable(instance: str, index: Optional[int] = None) -> str:
    """instance browser location name"""
    if index is not None:
        instance = get_instance_base(instance, index)
    return f"{instance}_missable"


def get_instance_capture(instance: str, index: Optional[int] = None) -> str:
    """instance capture location name"""
    if index is not None:
        instance = get_instance_base(instance, index)
    return f"{instance}_capture"


def get_loading_zone_name(from_: str, to: str) -> str:
    """loading zone name"""
    return f"{from_} -> {to}"


def get_mission_event(num: int) -> str:
    return f"COMPLETE_MISSION_{num:0>2}"


def get_quest_event(num: int) -> str:
    return f"COMPLETE_QUEST_{num:0>2}"


class PRSOAEvent(Enum):

    def __new__(cls, map_name: str):
        obj = object.__new__(cls)
        obj.map_name = map_name
        return obj

    @property
    def event_name(self) -> str:
        return f"EVENT_{self.name}"


class PREvent(PRSOAEvent):
    """Regular events"""

    SCHOOL_COLLECT_STYLERS = "m001_003a"
    SCHOOL_COMPLETE_NIGHT = "m001_011"

    GIVE_HAPPINY_TO_MIMI = "m009_002"
    RESCUE_PUELTOWN = "m010_003"


@dataclass(slots=True)
class InstanceEvent:
    map_name: str
    browser_id: int
    one_time: bool = True
    randomize: bool = False

    name: str = ""

    @property
    def event_name(self) -> str:
        return f"EVENT_P_{self.name}"


class EventRegistry:
    def __init_subclass__(cls):
        super().__init_subclass__()

        for attr_name, value in vars(cls).items():
            if isinstance(value, InstanceEvent) and not value.name:
                value.name = attr_name


class PInstanceEvent(EventRegistry):
    """MAP_NAME, BROWSER_ID"""

    """Script based """
    TUT_BIDOOF = InstanceEvent("m001_002", 4)  # quite sure these count for browser
    TIM_BIDOOF = InstanceEvent("m001_001", 4)  # 2 bidoof that attack Tim when leaving school

    TANGROWTH = InstanceEvent("m001_003b", 36)  # m0 graduation
    MILTANK = InstanceEvent("m004_001", 46)  # quest 1
    BUDEW_4 = InstanceEvent("m009_002", 8)  # m3 jump out at burning log

    RATATA_4 = InstanceEvent("m010_003", 67)  # m4 port
    Toxicroak = InstanceEvent("m010_003", 81)

    WAILORD = InstanceEvent("m029_009", 238)

    """Partners"""
    MACHOP = InstanceEvent("m041_001", 161)
    MISDREAVUS = InstanceEvent("m041_001", 220)
    SNEASEL = InstanceEvent("m041_001", 244)
    TURTWIG = InstanceEvent("m041_001", 52)
    CHIMCHAR = InstanceEvent("m041_001", 168)
    PIPLUP = InstanceEvent("m041_001", 206)
    STARLY = InstanceEvent("m041_001", 23)
    KRICKETOT = InstanceEvent("m041_001", 82)
    CRANIDOS = InstanceEvent("m041_001", 84)
    SHIELDON = InstanceEvent("m041_001", 181)
    PACHIRISU = InstanceEvent("m041_001", 26)
    MIME_JR = InstanceEvent("m041_001", 164)
    GIBLE = InstanceEvent("m041_001", 251)
    MUNCHLAX = InstanceEvent("m041_001", 27)
    HIPPOPOTAS = InstanceEvent("m041_001", 246)
    CROAGUNK = InstanceEvent("m041_001", 80)
    SNOVER = InstanceEvent("m041_001", 211)

    """DLC?"""
    DARKRAI = InstanceEvent("m041_001", 257, False)
    REGIGIGAS = InstanceEvent("m036_019", 267)
    DIALGA = InstanceEvent("m041_001", 435)
    PALKIA = InstanceEvent("m041_001", 436)
    SHAYMIN = InstanceEvent("m041_001", 437)

    @classmethod
    def events(cls):
        for name, event in vars(PInstanceEvent).items():
            if isinstance(event, InstanceEvent):
                yield event
