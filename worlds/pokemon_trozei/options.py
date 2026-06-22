from dataclasses import dataclass

from Options import PerGameCommonOptions, DeathLink, OptionGroup


class PokemonTrozeiDeathLink(DeathLink):
    __doc__ = (
        DeathLink.__doc__
        + "\n\n    In Pokemon Trozei, while in a stage in adventure mode, a game over is sent. "
          "Currently not implemented"
    )


@dataclass
class PokemonTrozeiOptions(PerGameCommonOptions):
    death_link: PokemonTrozeiDeathLink



OPTION_GROUPS = [
    OptionGroup(
        "deathlink",
        [
            PokemonTrozeiDeathLink
        ]
    )
]