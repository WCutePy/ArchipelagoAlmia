from enum import Enum
from typing import Optional


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

    pass


class PInstanceEvent(PRSOAEvent):
    MACHOP = ("Overworld", 161)
    MISDREAVUS = ("Overworld", 220)
    SNEASEL = ("Overworld", 244)
    TURTWIG = ("Overworld", 52)
    CHIMCHAR = ("Overworld", 168)
    PIPLUP = ("Overworld", 206)
    STARLY = ("Overworld", 23)
    KRICKETOT = ("Overworld", 82)
    CRANIDOS = ("Overworld", 84)
    SHIELDON = ("Overworld", 181)
    PACHIRISU = ("Overworld", 26)
    MIME_JR = ("Overworld", 164)
    GIBLE = ("Overworld", 251)
    MUNCHLAX = ("Overworld", 27)
    HIPPOPOTAS = ("Overworld", 246)
    CROAGUNK = ("Overworld", 80)
    SNOVER = ("Overworld", 211)

    WAILORD = ("m029_009", 238)
    REGIGIGAS = ("m036_019", 267)
    DARKRAI = ("Overworld", 257)
    DIALGA = ("Overworld", 435)
    PALKIA = ("Overworld", 436)
    SHAYMIN = ("Overworld", 437)

    def __new__(cls, map_name: str, browser_id: int, one_time: Optional[bool] = True):
        obj = object.__new__(cls)
        obj.map_name = map_name
        obj.browser_id = browser_id
        obj.one_time = one_time
        return obj

    @property
    def event_name(self) -> str:
        return f"EVENT_P_{self.name}"


print(PInstanceEvent)

for el in PInstanceEvent:
    print(el)
