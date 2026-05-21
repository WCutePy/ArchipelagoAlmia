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


def get_instance_capture(instance: str, index: Optional[int] = None) -> str:
    """instance capture location name"""
    if index is not None:
        instance = get_instance_base(instance, index)
    return f"{instance}_capture"


def get_loading_zone_name(from_: str, to: str) -> str:
    """loading zone name"""
    return f"{from_} -> {to}"


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


class PInstanceEvent(PRSOAEvent):
    """MAP_NAME, BROWSER_ID"""

    """Script based """
    TANGROWTH = ("m001_003b", 36)  # unsure about form
    MILTANK = ("m004_001", 46)



    WAILORD = ("m029_009", 238)


    """Partners"""
    MACHOP = ("m041_001", 161)
    MISDREAVUS = ("m041_001", 220)
    SNEASEL = ("m041_001", 244)
    TURTWIG = ("m041_001", 52)
    CHIMCHAR = ("m041_001", 168)
    PIPLUP = ("m041_001", 206)
    STARLY = ("m041_001", 23)
    KRICKETOT = ("m041_001", 82)
    CRANIDOS = ("m041_001", 84)
    SHIELDON = ("m041_001", 181)
    PACHIRISU = ("m041_001", 26)
    MIME_JR = ("m041_001", 164)
    GIBLE = ("m041_001", 251)
    MUNCHLAX = ("m041_001", 27)
    HIPPOPOTAS = ("m041_001", 246)
    CROAGUNK = ("m041_001", 80)
    SNOVER = ("m041_001", 211)

    """DLC?"""
    DARKRAI = ("m041_001", 257, False)
    REGIGIGAS = ("m036_019", 267)
    DIALGA = ("m041_001", 435)
    PALKIA = ("m041_001", 436)
    SHAYMIN = ("m041_001", 437)

    def __new__(cls, map_name: str, browser_id: int, one_time: Optional[bool] = True):
        obj = object.__new__(cls)
        obj.map_name = map_name
        obj.browser_id = browser_id
        obj.one_time = one_time
        return obj

    @property
    def event_name(self) -> str:
        return f"EVENT_P_{self.name}"
