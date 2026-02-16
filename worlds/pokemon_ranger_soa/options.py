from dataclasses import dataclass

from Options import Choice, OptionGroup, PerGameCommonOptions, Range, Toggle, DeathLink


class Goal(Choice):
    """
    The goal type for when the game is considered complete.
    Certain goals require configuring the exact amount/target
    in their specific option
    """

    display_name = "Goal type"

    option_mission_clear = 0
    option_quest_clear = 1
    option_capture_count = 2
    option_capture_rank_count = 3


class MissionClearTarget(Choice):
    """
    When mission clear is set as goal, this is the mission
    required to be beaten to complete the game.
    """

    display_name = "Missing clear target"

    option_rookie_soothe_the_pokemon_on_the_beach = 0
    option_deliver_vien_tribune = 1
    option_investigate_the_marine_cave = 2
    option_fight_the_forest_fire = 3
    option_destroy_the_strange_machines = 4
    option_recover_a_key_from_sharpedo = 5
    option_seek_the_origin_of_the_quake = 6
    option_teach_at_ranger_school = 7
    option_look_for_missing_barlow = 8
    option_support_sven_at_the_ruins = 9
    option_get_the_blue_gem = 10
    option_get_the_red_gem = 11
    option_rescue_wailord = 12
    option_reveal_the_hideout_secrets = 13
    option_get_the_yellow_gem = 14
    option_protect_ranger_union_hq = 15
    option_execute_operation_brighton = 16

    default = option_deliver_vien_tribune


class QuestClearTarget(Range):
    """
    Amount of quests required to clear to complete the game if
    quest clear is set as goal
    """

    display_name = "Quest clear target"

    range_start = 1
    range_end = 60
    default = 4


class CaptureCountTarget(Range):
    """
    Amount of Pokémon required to be captured in the browser
    to complete the game if this is set as goal.
    """

    display_name = "Capture count target"
    range_start = 1
    range_end = 270
    default = 30


class CaptureRankCountTarget(Range):
    """
    Amount of Pokémon that must be captured at the specified
    rank to complete the game if this is set as goal.
    """

    display_name = "Capture rank count target"
    range_start = 1
    range_end = 269
    default = 30


class CaptureRankRankTarget(Choice):
    """
    The rank at which each Pokémon must
    at least be captured in the browser if this is set as goal.

    C is not available as this would be equivalent
    to capturing the Pokémon regularly.
    """

    display_name = "Capture rank rank target"

    option_B = 0
    option_A = 1
    option_S = 2

    default = option_A


class PokemonRSOADeathLink(DeathLink):
    __doc__ = (
        DeathLink.__doc__
        + "\n\n    In Pokemon Emerald, whiting out sends a death and receiving a death causes you to white out."
    )


class DeathlinkDamage(Range):
    """
    Due to the punishing nature of deathlink in this game, whiting out back to your last
    save location, forcing you to actually use the save machines, deathlink
    will instead deal damage equal to a percentage of your total energy, rounded up.
    Set this to 100 to have deathlink auto kill you
    """

    display_name = "Death link health loss"
    range_start = 1
    range_end = 100
    default = 40


@dataclass
class PokemonRSOAOptions(PerGameCommonOptions):
    goal: Goal
    mission_clear_target: MissionClearTarget
    quest_clear_target: QuestClearTarget
    capture_count_target: CaptureCountTarget
    capture_rank_count_target: CaptureRankCountTarget
    capture_rank_rank_target: CaptureRankRankTarget

    death_link: PokemonRSOADeathLink
    death_link_damage: DeathlinkDamage


option_groups = [
    OptionGroup(
        "Goal options",
        [
            Goal,
            MissionClearTarget,
            QuestClearTarget,
            CaptureCountTarget,
            CaptureRankCountTarget,
            CaptureRankRankTarget,
        ],
    )
]
