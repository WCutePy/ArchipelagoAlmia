from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


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
    form_id: int = None
    browser_id: int = None
    one_time: bool = True
    randomize: bool = False
    mandatory: bool = False
    i: Optional[List[int]] = None
    m: Optional[int] = None

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
    """MAP_NAME, browser_id (original), form_id=new"""

    """Script based """
    TUT_BIDOOF = InstanceEvent(
        "m001_002", 173, i=[*range(4, 13)], m=0, mandatory=True
    )  # quite sure these count for browser
    NIGHT_PICHU = InstanceEvent("m001_006", 0x051)
    NIGHT_GHASTLY = InstanceEvent("m001_011", 0x02E)
    SLAKOTH = InstanceEvent(
        "m001_001", 129, i=[4], m=0, mandatory=True
    )  # stolen stylers
    TIM_BIDOOF = InstanceEvent(
        "m001_001", 310, i=[2, 3], m=0, mandatory=True
    )  # 2 bidoof that attack Tim when leaving school, fight only 1
    #
    TANGROWTH = InstanceEvent(
        "m001_003b", browser_id=36, mandatory=True
    )  # m0 graduation
    CAVE_ZUBAT = InstanceEvent(
        "m006_001", 20, mandatory=True
    )  # m2 spawn that is forced to fight
    MILTANK = InstanceEvent("m004_001", 113, i=[15], m=3, mandatory=True)  # quest 1
    BUDEW_4 = InstanceEvent(
        "m009_002", 180, i=[*range(12, 16)], m=3, mandatory=True
    )  # m3 jump out at burning log
    #
    RATATA_4 = InstanceEvent(
        "m010_003", 8, i=[*range(19, 23)], m=4, mandatory=True
    )  # m4 port
    TOXICROAK = InstanceEvent("m010_003", browser_id=81, mandatory=True)  # m4 port
    #
    KRICKETOT = InstanceEvent("m008_006", 175, mandatory=True)  # before m5
    CRANIDOS = InstanceEvent("m009_002", 182)
    WARTORTLE_WITH_CRANIDOS = InstanceEvent("m009_002", 4, i=[10], m=5)
    #
    SHARPEDO = InstanceEvent("m011_005", 237, mandatory=True)
    #
    RAMPARDOS = InstanceEvent(
        "m016_004", browser_id=2, mandatory=True
    )  # could be removed kinda, the capture might be early?
    #
    TURTWIG = InstanceEvent("m004_007", 161)  # after m6
    CROAGUNK = InstanceEvent("m002_001", 220, mandatory=True)  # m7
    CARNIVINE_2 = InstanceEvent(
        "m001_005", 222, i=[18, 19], m=7, mandatory=True
    )  # 2 of them
    #
    SLUGMA = InstanceEvent(
        "m019_003", 100, i=[3], m=8, mandatory=True
    )  # m8 together with magcargo
    MAGCARGO = InstanceEvent(
        "m019_003", 101, i=[4], m=8, mandatory=True
    )  # m8 together with slugma
    KANGASKHAN = InstanceEvent("m019_004", 57, i=[3], m=8, mandatory=True)  # m8
    NUMEL_3 = InstanceEvent("m019_004", 140, i=[4, 5, 6], m=8, mandatory=True)  # m8
    BEEDRIL_2 = InstanceEvent("m019_002", 7, i=[13, 14], m=8, mandatory=True)
    GLOOM = InstanceEvent("m019_002", 23, i=[12], m=8, mandatory=True)
    MACHOKE_2 = InstanceEvent("m020_001", 32, i=[2, 3], m=8, mandatory=True)  # in ship
    MIME_JR = InstanceEvent("m020_005", 210, mandatory=True)
    MAREEP_3 = InstanceEvent("m020_007", 82, i=[1, 2, 3], m=8, mandatory=True)
    MAGCARGO_3 = InstanceEvent(
        "m020_003", 101, i=[7, 8, 9], m=8, mandatory=True
    )  # in ship 3 at once
    RHYHORN_2 = InstanceEvent(
        "m020_008", 55, i=[2, 3, 4, 5], m=8, mandatory=True
    )  # top of ship
    STUNKY_3 = InstanceEvent(
        "m020_008", 205, i=[6, 7, 8], m=8, mandatory=True
    )  # top of ship
    DRAPION = InstanceEvent("m020_008", browser_id=174, mandatory=True)  # top of ship
    #
    SHIELDON = InstanceEvent("m016_003", 183)  # q036
    CHARMANDER = InstanceEvent("m019_002", 1)  # q013
    MURKROW_3 = InstanceEvent(
        "m022_001", 91, i=[8, 9, 10], m=9, mandatory=True
    )  # m9 enter highlands
    KOFFING_3 = InstanceEvent("m022_001", 53, i=[11, 12, 13], m=9, mandatory=True)
    # exist, but duplicates of the above!
    # MURKROW_2 = InstanceEvent("m022_001", 91, mandatory=True)  # with koffing 2
    # KOFFING_2 = InstanceEvent("m022_001", 53, mandatory=True)  # with murkrow 2
    SPIRITOMB = InstanceEvent("m023_015", browser_id=196, mandatory=True)  # bossfight
    #
    CHIMCHAR = InstanceEvent("m022_001", 164)  # q037
    BEEDRILl_2_Q = InstanceEvent("m022_001", 7, i=[5, 6], m=10)  # chimchar quest
    GOLBAT_3 = InstanceEvent("m024_004", 21, i=[1, 2, 3], m=10, mandatory=True)  # m10
    HOUNDOOM = InstanceEvent("m026_001", 109, i=[1, 2, 3], m=10, mandatory=True)  # m10
    HOUNDOUR_4 = InstanceEvent(
        "m028_001", 108, i=[3, 4, 5, 6], m=10, mandatory=True
    )  # m10
    SEEDOT_8 = InstanceEvent(
        "m028_020", 119, i=[*range(4, 12)], m=10, mandatory=True
    )  # m10
    FROSLASS = InstanceEvent("m028_022b", 423, mandatory=True)  # bossfight
    LUCARIO = InstanceEvent("m028_023", browser_id=223, mandatory=True)  # bossfight
    #
    PIPLUP = InstanceEvent("m026_001", 167)  # q045
    HOUNDOOM_Q = InstanceEvent("m026_001", 109, i=[11], m=11)  # q045 with piplup
    CHATOT_5 = InstanceEvent(
        "m019_014", 212, i=[*range(2, 7)], m=11
    )  # m11 - missable vanilla and randomized???
    BAGON_3 = InstanceEvent(
        "m019_006", 159, i=[2, 3, 4], m=11, mandatory=True
    )  # m11 with shelgon
    SHELGON = InstanceEvent(
        "m019_006", 160, i=[5], m=11, mandatory=True
    )  # m11 with bagon_3
    MONFERNO_2 = InstanceEvent("m019_011", 165, i=[6, 7], m=11, mandatory=True)  # m11
    INFERNAPE = InstanceEvent("m019_011", browser_id=170, mandatory=True)  # m11 boss
    HEATRAN = InstanceEvent("m019_012", browser_id=228, mandatory=True)  # m11 boss
    # m12
    SNOVER = InstanceEvent("m019_005", 226)  # q
    SEADRA = InstanceEvent(
        "m029_001", 59, i=[4], m=12, mandatory=True
    )  # m12 with horsea_2
    HORSEA_2 = InstanceEvent(
        "m029_001", 58, i=[5, 6], m=12, mandatory=True
    )  # m12 with seadra
    FINNEON_4 = InstanceEvent(
        "m029_002", 223, i=[1, 2, 3, 4], m=12, mandatory=True
    )  # m12
    STARMIE_3 = InstanceEvent("m029_002", 61, i=[6, 7, 8], m=12, mandatory=True)  # m12
    HUNTAIL = InstanceEvent(
        "m029_003", 157, i=[2], m=12, mandatory=True
    )  # together with gorebyss
    GOREBYSS = InstanceEvent(
        "m029_003", 158, i=[3], m=12, mandatory=True
    )  # together with huntail
    KINGDRA = InstanceEvent("m029_001", browser_id=231, mandatory=True)  # boss
    # m13
    WAILORD = InstanceEvent(
        "m029_001", browser_id=238, mandatory=True
    )  # friendship technically past m12, but no fight yet
    JOLTEON = InstanceEvent("m030_008", 71, i=[1], m=13)  #  missable randomized
    CACNEA_2 = InstanceEvent("m030_009", 143, i=[1, 2], m=13, mandatory=True)
    SLAKOTH_8 = InstanceEvent(
        "m030_016", 129, i=[7, *range(12, 19)], m=13, mandatory=True
    )
    VICTREEBEL = InstanceEvent(
        "m030_013", 34, i=[1], m=13
    )  #  missable vanilla and randomized, together with mothim
    MOTHIM = InstanceEvent("m030_013", 185, i=[2], m=13)  # missable
    MURKROW = InstanceEvent(
        "m030_012", 91, i=[2], m=13
    )  # missable together with honchkrow
    HONCHKROW = InstanceEvent(
        "m030_012", 201, i=[3], m=13
    )  # missable together with murkrow
    MR_MIME_2 = InstanceEvent("m030_015", 62, i=[5, 6], m=13, mandatory=True)
    MOTHIM_2 = InstanceEvent("m030_018", 185, i=[1, 2], m=13, mandatory=True)
    SKUNTANK_2 = InstanceEvent("m030_019", 206, i=[1, 2], m=13, mandatory=True)
    MACHAMP_2 = InstanceEvent("m030_020", 33, i=[1, 2], m=13, mandatory=True)
    GLISCOR = InstanceEvent("m030_022", browser_id=129, mandatory=True)  # boss
    # m14
    CRESSELIA = InstanceEvent("m036_017", browser_id=254, mandatory=True)  # boss
    SNEASEL = InstanceEvent("m028_009", 99)  # q
    MISDREAVUS = InstanceEvent("m023_005", 92)  # q
    # m15
    MAGNEZONE = InstanceEvent("m036_016", browser_id=64, mandatory=True)  # boss
    CLAYDOL_2 = InstanceEvent("m036_009", 146, i=[1, 2], m=15)  # q
    ELECTIVIRE = InstanceEvent("m017_002", browser_id=72, mandatory=True)  # boss
    GARCHOMP = InstanceEvent("m017_003a", browser_id=253, mandatory=True)  # boss
    BIDOOF_8 = InstanceEvent("m017_007", 173, i=[*range(12, 20)], m=15, mandatory=True)
    # m16
    YANMEGA = InstanceEvent("m014_002", browser_id=119, mandatory=True)  # boss
    WEEZING = InstanceEvent(
        "m038_001", 54, i=[8], m=16, mandatory=True
    )  # with skuntank
    SKUNTANK = InstanceEvent(
        "m038_001", 206, i=[9], m=16, mandatory=True
    )  # with weezing
    SHIFTRY = InstanceEvent(
        "m038_001", 121, i=[7], m=16, mandatory=True
    )  # with nuzleaf_2
    NUZLEAF_2 = InstanceEvent("m038_001", 120, mandatory=True)  # with shiftry
    PRIMEAPE = InstanceEvent("m038_002", 26, i=[2], m=16)  # in elevator, very missable
    ELECTRODE = InstanceEvent("m038_002", 52, i=[3], m=16)  # in elevator, very missable
    DUSCLOPS_2 = InstanceEvent(
        "m038_002", 150, i=[1], m=16, mandatory=True
    )  # also elevator
    MUK = InstanceEvent("m038_002", 45, i=[4], m=16)  # supposedly also elevator!!!
    GABITE_3 = InstanceEvent("m038_019", 214, i=[4], m=16, mandatory=True)
    GENGAR_2 = InstanceEvent("m038_019", 48, i=[5, 6], m=16, mandatory=True)
    MAMOSWINE = InstanceEvent("m038_019", 420, i=[7], m=16, mandatory=True)
    MISMAGIUS = InstanceEvent(
        "m038_007", 200, mandatory=True, randomize=False
    )  # with banette, uses npc sprite
    BANETTE = InstanceEvent(
        "m038_007", 148, mandatory=True, randomize=False
    )  # with mismagius
    ESPEON = InstanceEvent("m038_006", 89, i=[1], m=16, mandatory=True)  # with umbreon
    UMBREON = InstanceEvent("m038_006", 90, mandatory=True)  # with espeon
    BRONZONG = InstanceEvent(
        "m038_009", 208, i=[2], m=16, mandatory=True
    )  # with claydol
    CLAYDOL = InstanceEvent("m038_009", 146, mandatory=True)  # with bronzong
    AGGRON = InstanceEvent(
        "m038_011", 138, mandatory=True, randomize=False
    )  # with tyranitar # npc sprite
    TYRANITAR = InstanceEvent(
        "m038_011", 116, mandatory=True, randomize=False
    )  # with aggron
    BLAZIKEN_2 = InstanceEvent("m038_003", 118, i=[6], m=16, mandatory=True)
    SPINARAK_5 = InstanceEvent("m038_012", 76, i=[8, 9, 10], m=16, mandatory=True)
    ALAKAZAM = InstanceEvent(
        "m038_016", 30, i=[1], m=16, mandatory=True
    )  # with sceptile and luxray
    SCEPTILE = InstanceEvent(
        "m038_016", 117, mandatory=True
    )  # with alakazam and luxray
    LUXRAY = InstanceEvent("m038_016", 179, mandatory=True)
    SKORUPI_3 = InstanceEvent("m038_012", 219, i=[11, 12, 13], m=16, mandatory=True)
    BRONZOR_3 = InstanceEvent("m038_012", 207, i=[14, 15, 16], m=16, mandatory=True)
    BELLOSSOM_3 = InstanceEvent("m038_012", 85, i=[17, 18, 19], m=16, mandatory=True)
    CACTURNE_3 = InstanceEvent("m038_012", 144, i=[20, 21, 22], m=16, mandatory=True)
    VAPOREON = InstanceEvent(
        "m038_012", 70, i=[24], m=16, mandatory=True
    )  # with jolteon_f10 and flareon
    JOLTEON_F10 = InstanceEvent(
        "m038_012", 71, i=[25], m=16, mandatory=True
    )  # with vaporeon and flareon
    FLAREON = InstanceEvent(
        "m038_012", 72, i=[23], m=16, mandatory=True
    )  # with vaporeon and jolteon f10
    SCIZOR = InstanceEvent(
        "m038_018", 98, i=[6], m=16, mandatory=True
    )  # with gardevoir
    GARDEVOIR = InstanceEvent(
        "m038_018", 128, i=[7], m=16, mandatory=True
    )  # with scizor
    RHYPERIOR = InstanceEvent("m039_004a", browser_id=151, mandatory=True)  # boss
    MAGMORTAR = InstanceEvent("m039_006a", browser_id=75, mandatory=True)  # boss
    GALLADE = InstanceEvent("m039_008a", browser_id=160, mandatory=True)  # boss
    RHYPERIOR_AGAIN = InstanceEvent(
        "m039_008a", 415, mandatory=True, randomize=False
    )  # with magmortar and gallade
    MAGMORTAR_AGAIN = InstanceEvent(
        "m039_008a", 417, mandatory=True, randomize=False
    )  # with rhyperior and gallade
    GALLADE_AGAIN = InstanceEvent(
        "m039_008a", 438, mandatory=True, randomize=False
    )  # with rhyperior and magmortar
    BIDOOF_TOWER = InstanceEvent("m039_010a", 173, i=[0], m=16, mandatory=True)
    DUSKNOIR = InstanceEvent("m039_010a", browser_id=192, mandatory=True)  # boss
    DARKRAI = InstanceEvent(
        "m039_010a", browser_id=257, mandatory=True
    )  # boss, technically b

    # """Partners"""
    # MACHOP = InstanceEvent("m041_001", browser_id=161)
    # STARLY = InstanceEvent("m041_001", browser_id=23)
    # PACHIRISU = InstanceEvent("m041_001", browser_id=26)
    # GIBLE = InstanceEvent("m041_001", browser_id=251)
    # MUNCHLAX = InstanceEvent("m041_001", browser_id=27)
    # HIPPOPOTAS = InstanceEvent("m041_001", browser_id=246)
    #
    # """DLC?"""
    # REGIGIGAS = InstanceEvent("m036_019", browser_id=267)
    # DIALGA = InstanceEvent("m041_001", browser_id=435)
    # PALKIA = InstanceEvent("m041_001", browser_id=436)
    # SHAYMIN = InstanceEvent("m041_001", browser_id=437)

    @classmethod
    def events(cls):
        for name, event in vars(PInstanceEvent).items():
            if isinstance(event, InstanceEvent):
                yield event
