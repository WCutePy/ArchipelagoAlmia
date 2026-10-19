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
    mandatory: bool = False

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
    TUT_BIDOOF = InstanceEvent(
        "m001_002", 4, mandatory=True
    )  # quite sure these count for browser
    SLAKOTH = InstanceEvent("m001_001", 32, mandatory=True)  # stolen stylers
    TIM_BIDOOF = InstanceEvent(
        "m001_001", 4, mandatory=True
    )  # 2 bidoof that attack Tim when leaving school, fight only 1
    #
    TANGROWTH = InstanceEvent("m001_003b", 36, mandatory=True)  # m0 graduation
    MILTANK = InstanceEvent("m004_001", 46, mandatory=True)  # quest 1
    BUDEW_4 = InstanceEvent("m009_002", 8, mandatory=True)  # m3 jump out at burning log
    #
    RATATA_4 = InstanceEvent("m010_003", 67, mandatory=True)  # m4 port
    TOXICROAK = InstanceEvent("m010_003", 81, mandatory=True)  # m4 port
    #
    KRICKETOT = InstanceEvent("m008_006", 82, mandatory=True)  # before m5
    CRANIDOS = InstanceEvent("m009_002", 84)
    WARTORTLE_WITH_CRANIDOS = InstanceEvent("m009_002", 12)
    #
    RAMPARDOS = InstanceEvent(
        "m016_004", 2, mandatory=True
    )  # could be removed kinda, the capture might be early?
    #
    TURTWIG = InstanceEvent("m004_007", 52)  # after m6
    CROAGUNK = InstanceEvent("m002_001", 80, mandatory=True)  # m7
    CARNIVINE_2 = InstanceEvent("m001_005", 136, mandatory=True)  # 2 of them
    #
    SLUGMA = InstanceEvent("m019_003", 140, mandatory=True)  # m8
    MAGCARGO = InstanceEvent("m019_003", 141, mandatory=True)  # m8 together with slugma
    KANGASKHAN = InstanceEvent("m019_004", 146, mandatory=True)  # m8
    NUMEL_3 = InstanceEvent("m019_004", 124, mandatory=True)  # m8
    BEEDRIL_2 = InstanceEvent("m019_002", 58, mandatory=True)
    GLOOM = InstanceEvent("m019_002", 115, mandatory=True)
    MACHOKE_2 = InstanceEvent("m020_001", 162, mandatory=True)  # in ship
    MIME_JR = InstanceEvent("m020_005", 164, mandatory=True)
    MAREEP_3 = InstanceEvent("m020_007", 105, mandatory=True)
    MAGCARGO_3 = InstanceEvent("m020_003", 141, mandatory=True)  # in ship 3 at once
    RHYHORN_2 = InstanceEvent("m020_008", 149, mandatory=True)  # top of ship
    STUNKY_3 = InstanceEvent("m020_008", 144, mandatory=True)  # top of ship
    DRAPION = InstanceEvent("m020_008", 174, mandatory=True)  # top of ship
    #
    SHIELDON = InstanceEvent("m016_003", 181)  # q036
    CHARMANDER = InstanceEvent("m019_002", 137)  # q013
    MURKROW_3 = InstanceEvent("m022_001", 185, mandatory=True)  # m9 enter highlands
    KOFFING_3 = InstanceEvent("m022_001", 187, mandatory=True)
    MURKROW_2 = InstanceEvent("m022_001", 185, mandatory=True)  # with koffing 2
    KOFFING_2 = InstanceEvent("m022_001", 187, mandatory=True)  # with murkrow 2
    SPIRITOMB = InstanceEvent("m023_015", 196, mandatory=True)  # bossfight
    #
    CHIMCHAR = InstanceEvent("m022_001", 168)  # q037
    BEEDRILl_2_Q = InstanceEvent("m022_001", 58)  # chimchar quest
    GOLBAT_3 = InstanceEvent("m024_004", 15, mandatory=True)  # m10
    HOUNDOOM = InstanceEvent("m026_001", 154, mandatory=True)  # m10
    HOUNDOUR_4 = InstanceEvent("m028_001", 153, mandatory=True)  # m10
    SEEDOT_8 = InstanceEvent("m028_020", 33, mandatory=True)  # m10
    FROSLASS = InstanceEvent("m028_022b", 215, mandatory=True)  # bossfight
    LUCARIO = InstanceEvent("m028_023", 223, mandatory=True)  # bossfight
    #
    PIPLUP = InstanceEvent("m026_001", 206)  # q045
    HOUNDOOM_Q = InstanceEvent("m026_001", 154)  # q045 with piplup
    CHATOT_5 = InstanceEvent("m019_014", 69)  # m11 - missable vanilla and randomized???
    BAGON_3 = InstanceEvent("m019_006", 225, mandatory=True)  # m11 with shelgon
    SHELGON = InstanceEvent("m019_006", 226, mandatory=True)  # m11 with bagon_3
    MONFERNO_2 = InstanceEvent("m019_011", 169, mandatory=True)  # m11
    INFERNAPE = InstanceEvent("m019_011", 170, mandatory=True)  # m11 boss
    HEATRAN = InstanceEvent("m019_012", 228, mandatory=True)  # m11 boss
    # m12
    SNOVER = InstanceEvent("m019_005", 211)  # q
    SEADRA = InstanceEvent("m029_001", 230, mandatory=True)  # m12 with horsea_2
    HORSEA_2 = InstanceEvent("m029_001", 229, mandatory=True)  # m12 with seadra
    FINNEON_4 = InstanceEvent("m029_002", 86, mandatory=True)  # m12
    STARMIE_3 = InstanceEvent("m029_002", 95, mandatory=True)  # m12
    HUNTAIL = InstanceEvent("m029_003", 232, mandatory=True)  # together with gorebyss
    GOREBYSS = InstanceEvent("m029_003", 233, mandatory=True)  # together with huntail
    KINGDRA = InstanceEvent("m029_001", 231, mandatory=True)  # boss
    # m13
    WAILORD = InstanceEvent(
        "m029_001", 238, mandatory=True
    )  # friendship technically past m12, but no fight yet
    JOLTEON = InstanceEvent("m030_008", 99)  #  missable randomized
    CACNEA_2 = InstanceEvent("m030_009", 239, mandatory=True)
    SLAKOTH_8 = InstanceEvent("m030_016", 32, mandatory=True)
    VICTREEBEL = InstanceEvent(
        "m030_013", 242
    )  #  missable vanilla and randomized, together with mothim
    MOTHIM = InstanceEvent("m030_013", 241)  # missable
    MURKROW = InstanceEvent("m030_012", 185)  # missable together with honchkrow
    HONCHKROW = InstanceEvent("m030_012", 186)  # missable together with murkrow
    MR_MIME = InstanceEvent("m030_015", 165, mandatory=True)
    MOTHIM_2 = InstanceEvent("m030_018", 241, mandatory=True)
    SKUNTANK_2 = InstanceEvent("m030_019", 145, mandatory=True)
    MACHAMP_2 = InstanceEvent("m030_020", 163, mandatory=True)
    GLISCOR = InstanceEvent("m030_022", 129, mandatory=True)  # boss
    # m14
    CRESSELIA = InstanceEvent("m036_017", 254, mandatory=True)  # boss
    SNEASEL = InstanceEvent("m028_009", 244)  # q
    MISDREAVUS = InstanceEvent("m023_005", 220)  # q
    # m15
    MAGNEZONE = InstanceEvent("m036_016", 64, mandatory=True)  # boss
    CLAYDOL_2 = InstanceEvent("m036_009", 250)  # q
    ELECTIVIRE = InstanceEvent("m017_002", 72, mandatory=True)  # boss
    GARCHOMP = InstanceEvent("m017_003a", 253, mandatory=True)  # boss
    BIDOOF_8 = InstanceEvent("m017_007", 4, mandatory=True)
    # m16
    YANMEGA = InstanceEvent("m014_002", 119, mandatory=True)  # boss
    WEEZING = InstanceEvent("m038_001", 188, mandatory=True)  # with skuntank
    SKUNTANK = InstanceEvent("m038_001", 145, mandatory=True)  # with weezing
    SHIFTRY = InstanceEvent("m038_001", 35, mandatory=True)  # with nuzleaf_2
    NUZLEAF_2 = InstanceEvent("m038_001", 34, mandatory=True)  # with shiftry
    PRIMEAPE = InstanceEvent("m038_002", 127)  # in elevator, very missable
    ELECTRODE = InstanceEvent("m038_002", 77)  # in elevator, very missable
    DUSCLOPS_2 = InstanceEvent("m038_002", 191, mandatory=True)  # also evelator
    GABITE_3 = InstanceEvent("m038_019", 252, mandatory=True)
    GENGAR_2 = InstanceEvent("m038_019", 19, mandatory=True)
    MAMOSWINE = InstanceEvent("m030_019", 202, mandatory=True)
    BRONZONG = InstanceEvent("m038_009", 249, mandatory=True)  # with claydol
    CLAYDOL = InstanceEvent("m038_009", 250, mandatory=True)  # with bronzong
    AGGRON = InstanceEvent("m038_011", 133, mandatory=True)  # with tyranitar
    TYRANITAR = InstanceEvent("m038_011", 122, mandatory=True)  # with aggron
    MISMAGIUS = InstanceEvent("m038_007", 221, mandatory=True)  # with banette
    BANETTE = InstanceEvent("m038_007", 148, mandatory=True)  # with mismagius
    ESPEON = InstanceEvent("m038_006", 101, mandatory=True)  # with umbreon
    UMBREON = InstanceEvent("m038_006", 102, mandatory=True)  # with espeon
    BLAZIKEN_2 = InstanceEvent("m038_003", 255, mandatory=True)
    SPINARAK_5 = InstanceEvent("m038_012", 155, mandatory=True)
    ALAKAZAM = InstanceEvent(
        "m038_016", 184, mandatory=True
    )  # with sceptile and luxray
    SCEPTILE = InstanceEvent(
        "m038_016", 243, mandatory=True
    )  # with alakazam and luxray
    LUXRAY = InstanceEvent("m038_016", 51, mandatory=True)
    SKORUPI_3 = InstanceEvent("m038_012", 173, mandatory=True)
    BRONZOR_3 = InstanceEvent("m038_012", 248, mandatory=True)
    BELLOSSOM_3 = InstanceEvent("m038_012", 117, mandatory=True)
    CACTURNE_3 = InstanceEvent("m038_012", 240, mandatory=True)
    VAPOREON = InstanceEvent(
        "m038_012", 98, mandatory=True
    )  # with jolteon_f10 and flareon
    JOLTEON_F10 = InstanceEvent(
        "m038_012", 99, mandatory=True
    )  # with vaporeon and flareon
    FLAREON = InstanceEvent(
        "m038_012", 100, mandatory=True
    )  # with vaporeon and jolteon f10
    SCIZOR = InstanceEvent("m038_018", 217, mandatory=True)  # with gardevoir
    GARDEVOIR = InstanceEvent("m038_018", 159, mandatory=True)  # with scizor
    RHYPERIOR = InstanceEvent("m039_004a", 151, mandatory=True)  # boss
    MAGMORTAR = InstanceEvent("m039_006a", 75, mandatory=True)  # boss
    GALLADE = InstanceEvent("m039_002", 160, mandatory=True)  # boss
    RHYPERIOR_AGAIN = InstanceEvent(
        "m039_002", 151, mandatory=True
    )  # with magmortar and gallade
    MAGMORTAR_AGAIN = InstanceEvent(
        "m039_002", 75, mandatory=True
    )  # with rhyperior and gallade
    GALLADE_AGAIN = InstanceEvent(
        "m039_002", 160, mandatory=True
    )  # with rhyperior and magmortar
    BIDOOF_TOWER = InstanceEvent("m039_010a", 4, mandatory=True)
    DUSKNOIR = InstanceEvent("m039_010a", 192, mandatory=True)  # boss
    DARKRAI = InstanceEvent("m039_010a", 257, mandatory=True)  # boss, technically b

    # """Partners"""
    # MACHOP = InstanceEvent("m041_001", 161)
    # STARLY = InstanceEvent("m041_001", 23)
    # PACHIRISU = InstanceEvent("m041_001", 26)
    # GIBLE = InstanceEvent("m041_001", 251)
    # MUNCHLAX = InstanceEvent("m041_001", 27)
    # HIPPOPOTAS = InstanceEvent("m041_001", 246)
    #
    # """DLC?"""
    # REGIGIGAS = InstanceEvent("m036_019", 267)
    # DIALGA = InstanceEvent("m041_001", 435)
    # PALKIA = InstanceEvent("m041_001", 436)
    # SHAYMIN = InstanceEvent("m041_001", 437)

    @classmethod
    def events(cls):
        for name, event in vars(PInstanceEvent).items():
            if isinstance(event, InstanceEvent):
                yield event
