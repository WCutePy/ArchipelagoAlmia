from dataclasses import dataclass

from BaseClasses import PlandoOptions
from Options import (
    Choice,
    OptionGroup,
    PerGameCommonOptions,
    Range,
    Toggle,
    DeathLink,
    OptionList,
    OptionError,
)
from .data import data
from ..AutoWorld import World


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
    When mission clear is set as goal, this is the
    mission/story section required to be
    beaten to complete the game.
    """

    display_name = "Missing clear target"

    option_graduate_school = 0
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

    default = option_investigate_the_marine_cave


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


class LevelUpType(Choice):
    """
    Lets you choose if level up is locked behind progressive level up.
    The progression items will automatically level you up to the next stat cap.

    Lets you choose between not modifying it,
    Having separate progression items for Power and Energy or
    having both together.
    """

    display_name = "Option to modify how leveling up works"

    option_vanilla = 0
    option_separate = 1
    option_together = 2

    default = option_separate


class LevelUpCount(Range):
    """
    The amount of level up items in the pool.
    Regardless of setting,
    Leveling beyond 99 is not possible.
    """

    display_name = "Level up items"

    range_start = 1
    range_end = 98

    default = 10


class LevelUpIncrement(Range):
    """
    Each level up progression item will level you up by this
    amount of levels. Leveling beyond 99 is not possible.
    """

    display_name = "Level up increment"

    range_start = 1
    range_end = 98

    default = 4


class RankUpType(Choice):
    """
    Choose between ranking up vanilla or as progression item.
    """

    display_name = "Rank up type"

    option_vanilla = 0
    option_item = 1

    default = option_item


class RankUpItemCount(Range):
    """
    Rank is logically required for certain locations.
    Selecting below 10 rank items restricts what is
    accessible.
    """

    display_name = "Rank up items"

    range_start = 0
    range_end = 15
    default = 10


class RankUpIncrement(Range):
    """
    How much Ranger Rank will increment for each Rank up item
    """

    display_name = "Rank up increment"

    range_start = 1
    range_end = 10

    default = 1


class StylerModelItem(Choice):
    """
    Determines if the styler models
    School, Capture, ... are provided vanilla
    or as an item.
    """

    auto_display_name = True

    option_vanilla = 0
    option_item = 1

    default = 1


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


class FieldMoveItem(Choice):
    """
    If this is on, all Field moves are locked
    behind their respective items.
    Not all field moves might be included as item
    based on available locations and will always be locked.
    """

    auto_display_name = True

    option_vanilla = 0
    option_item = 1

    default = option_item


class FieldMoveLevelItem(Range):
    """
    If this is higher than 1, Each Fieldmove with multiple levels turns
    into a progressive field move. The maximum field moves for each
    level is the maximum available level.

    For moves that go up to 5:

    1: 5
    2: 2 - 5
    3: 1 - 3 - 5
    4: 1 - 2 - 3 - 5
    5: 1 - 2 - 3 - 4 - 5

    Moves that go up to 3:
    1: 3
    2: 1 - 3
    3: 1 - 2 - 3
    """

    auto_display_name = True
    range_start = 1
    range_end = 5

    default = 1


class RandomizePokemon(Choice):
    auto_display_name = True

    option_vanilla = 0
    option_full_random = 1
    # option_field_move_replacement = 2
    # option_full_random_with_softlock = 3

    default = option_full_random


class RandomizePartners(Choice):
    auto_display_name = True

    option_vanilla = 0
    option_all_random = 1
    option_starter_only = 2
    default = option_all_random


partner_blacklist = {
    238,  # wailord
}


class PartnerStarters(OptionList):
    auto_display_name = True

    valid_keys_casefold = True
    valid_keys = [
        data.name for i, data in data.species.items() if i not in partner_blacklist
    ]

    def verify(
        self, world: type[World], player_name: str, plando_options: PlandoOptions
    ) -> None:
        super().verify(world, player_name, plando_options)

        errors = []

        if len(self.value) > 3:
            errors.append(
                f"A maximum of 3 starters can be listed. {len(self.value)} have been given."
            )

        if len(errors) != 0:
            errors = [
                f"For option {getattr(self, 'display_name', self)} of player {player_name}:"
            ] + errors
            raise OptionError("\n".join(errors))


class Partners(OptionList):
    auto_display_name = True

    valid_keys_casefold = True
    valid_keys = [
        data.name for i, data in data.species.items() if i not in partner_blacklist
    ]

    def verify(
        self, world: type[World], player_name: str, plando_options: PlandoOptions
    ) -> None:
        super().verify(world, player_name, plando_options)

        errors = []

        if len(self.value) > 18:
            errors.append(
                f"A maximum of 18 starters can be set. {len(self.value)} have been given."
            )

        if len(errors) != 0:
            errors = [
                f"For option {getattr(self, 'display_name', self)} of player {player_name}:"
            ] + errors
            raise OptionError("\n".join(errors))


class RandomizeTargetFieldMove(Choice):
    auto_display_name = True

    option_vanilla = 0
    option_full_random = 1
    option_same_level = 2

    default = option_vanilla


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

    level_up_type: LevelUpType
    level_up_count: LevelUpCount
    level_up_increment: LevelUpIncrement

    rank_up_type: RankUpType
    rank_up_count: RankUpItemCount
    rank_up_increment: RankUpIncrement

    styler_model_item: StylerModelItem

    field_move_item: FieldMoveItem
    field_move_levels: FieldMoveLevelItem

    randomize_pokemon: RandomizePokemon
    randomize_partners: RandomizePartners
    partner_starters: PartnerStarters
    partners: Partners
    randomize_target_field_move: RandomizeTargetFieldMove

    def verify(self):
        errors = []

        if len(self.partners.value) > (18 - len(self.partner_starters.value)):
            errors.append(
                f"{len(self.partner_starters.value)} starter partners have been specified. A maximum of {18 - len(self.partner_starters.value)} can be set"
            )

        if len(errors) != 0:
            errors = [
                f"For option {getattr(self, 'display_name', self)} of player {player_name}:"
            ] + errors
            raise OptionError("\n".join(errors))


OPTION_GROUPS = [
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
    ),
    OptionGroup("Level up", [LevelUpType, LevelUpCount, LevelUpIncrement]),
    OptionGroup("Rank up", [RankUpType, RankUpItemCount, RankUpIncrement]),
    OptionGroup(
        "Randomization",
        [
            RandomizePokemon,
            RandomizeTargetFieldMove,
        ],
    ),
    OptionGroup("Partners", [RandomizePartners, PartnerStarters, Partners]),
]
