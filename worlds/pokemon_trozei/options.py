from dataclasses import dataclass

from Options import PerGameCommonOptions, DeathLink, OptionGroup, Range, Choice


class RequiredBossesCount(Range):
    """
    Sets the number of mini bosses required to be able to challenge phobosphere.
    To unlock phobosphere this therefore requires the mini boss level unlocks
    and the phobosphere level unlock
    """

    display_name = "Required bosses count"
    range_start = 1
    range_end = 5
    default = 5


class HardModeAdventure(Choice):
    """
    Allows playing the adventure in hard mode. This makes the game a little harder.
    It is possible to play on normal, start on hard mode or have hard mode turned
    on by a trap item and stay on permanently.
    """

    display_name = "Hard mode adventure"
    option_normal = 0
    option_hard = 1
    option_hard_as_trap = 2

    default = 0


class HardTrapCount(Range):
    """
    Specifies the amount of hard mode traps added to the item pool
    when set to hard as trap.
    """

    range_start = 1
    range_end = 5
    default = 1


class PokemonTrozeiDeathLink(DeathLink):
    __doc__ = (
        DeathLink.__doc__
        + "\n\n    In Pokemon Trozei, while in a stage in adventure mode, a game over is sent. "
        "Game over sends a death link."
    )


@dataclass
class PokemonTrozeiOptions(PerGameCommonOptions):
    required_bosses: RequiredBossesCount
    hard_mode: HardModeAdventure
    hard_trap_count: HardTrapCount
    death_link: PokemonTrozeiDeathLink


OPTION_GROUPS = [
    OptionGroup("gameplay", [RequiredBossesCount, HardModeAdventure, HardTrapCount]),
    OptionGroup("deathlink", [PokemonTrozeiDeathLink]),
]
