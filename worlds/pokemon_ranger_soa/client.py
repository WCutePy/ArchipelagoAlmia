import asyncio
import copy
import orjson
import random
import time
from typing import TYPE_CHECKING, Optional, Dict, Set, Tuple, List
import uuid

from NetUtils import ClientStatus
from Options import Toggle
import Utils
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from worlds._bizhawk.client import BizHawkClient

from .data import (
    data,
    ItemCategory,
    ItemData,
    GameStateEnum,
    LocationCategory,
    location_category_to_id,
    FieldMoveCategory,
    POKE_ID_ROW_RAM_SIZE,
)
from . import items, options
from .items import offset_item_value

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

RECEIVED_ITEM_ADDRESS = data.ram_addresses["RECEIVED_ITEM_ADDRESS"]
NOP_INSTRUCTION_BYTES = bytes.fromhex("0000A0E3")


class PokemonRangerSOA(BizHawkClient):
    game = "PokemonRangerSOA"
    system = "NDS"
    patch_suffix = ".apprsoa"

    local_checked_locations: Set[int]
    local_set_events: Dict[str, bool]
    local_found_key_items: Dict[str, bool]
    local_captured_pokemon: int

    goal_flag: Optional[int]

    death_counter: Optional[int]
    previous_death_link: float
    ignore_next_death_link: bool

    current_map_id: Optional[int]

    level: int
    energy: int
    has_energy_plus: bool
    styler_model: int

    level_up_patched: bool

    partner_quests = Set[int]
    first_partner = Optional[int]
    allowed_partners = Set[int]

    def initialize_client(self):
        self.local_checked_locations = set()
        self.local_set_events = {}
        self.local_found_key_items = {}
        self.local_captured_pokemon = 0
        self.goal_flag = None
        self.death_counter = None
        self.previous_death_link = 0
        self.ignore_next_death_link = False
        self.current_map_id = None
        self.level_up_patched = False
        self.has_energy_plus = False
        self.styler_model = 0
        self.partner_quests = set()
        self.first_partner = None
        self.allowed_partners = set()

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:

        ctx.game = self.game
        ctx.items_handling = 0b001
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.125

        self.initialize_client()

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None:
            return

        if not ctx.items_handling & 0b010:
            ctx.items_handling = 0b011
            Utils.async_start(
                ctx.send_msgs(
                    [{"cmd": "ConnectUpdate", "items_handling": ctx.items_handling}]
                )
            )

            await asyncio.sleep(0.75)
            return

        try:
            guards: Dict[str, Tuple[int, bytes, str]] = {}

            await self.handle_tracker_info(ctx, guards)
            await self.handle_death_link(ctx, guards)

            game_state = None
            browser_captures_bytes = bytes(0)
            quest_bytes = bytes(0)

            num_receieved_items = 0
            styler_and_rank = None
            current_mission = None
            room_id = None
            partner_pokemon = bytes(0)

            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (data.ram_addresses["GAME_STATE"].first, 1, "ARM9 System Bus"),
                    (
                        data.ram_addresses["BROWSER_TABLE_ADDRESS"].first,
                        0x7A,
                        "ARM9 System Bus",
                    ),
                    (RECEIVED_ITEM_ADDRESS.first, 3, "ARM9 System Bus"),
                    (
                        data.ram_addresses["CURRENT_STYLER_AND_RANK"].first,
                        1,
                        "ARM9 System Bus",
                    ),
                    (data.ram_addresses["CURRENT_MISSION"].first, 1, "ARM9 System Bus"),
                    (data.ram_addresses["CURRENT_ROOM_ID"].first, 2, "ARM9 System Bus"),
                    (
                        data.ram_addresses["QUEST_TABLE_ADDRESS"].first,
                        60,
                        "ARM9 System Bus",
                    ),
                    (
                        data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first,
                        10,
                        "ARM9 System Bus",
                    ),
                ],
            )

            if read_result is not None:
                game_state = int.from_bytes(read_result[0], "little")
                browser_captures_bytes = read_result[1]
                num_receieved_items = int.from_bytes(read_result[2], "little")
                styler_and_rank = int.from_bytes(read_result[3], "little")
                current_mission = int.from_bytes(read_result[4], "little")
                room_id = int.from_bytes(read_result[5], "little")
                quest_bytes = read_result[6]
                partner_pokemon = read_result[7]

            if (
                ctx.slot_data["level_up_type"] != options.LevelUpType.option_vanilla
                and game_state == GameStateEnum.BATTLE
            ):
                if not self.level_up_patched:
                    # await self.patch_level_up_instructions(ctx)
                    self.level_up_patched = True
                return
            self.level_up_patched = False

            """
            BEING IN BATTLE WILL STOP THINGS BELOW OCCURRING!
            AT THE MOMENT THE SOMETHING IS LAGGY, THIS IS TO REDUCE
            LAG IN COMBAT.
            """

            if (
                ctx.slot_data["styler_model_item"]
                != options.StylerModelItem.option_vanilla
                and (current_mission == 0x01)  # means it's AFTER the ingame upgrade
                and ((styler_and_rank >> 4) & 0xF != self.styler_model)
            ):
                item = next(
                    i for i in data.items.values() if i.label == "Progressive Styler"
                )
                # can be replaced with id when more stable / settled on static ids.
                item_id = offset_item_value(item.item_id)

                output = await self.handle_player_attributes(ctx, item, item_id)
                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    output,
                )

            partner_counts_as_party_slot = partner_pokemon[8]
            partner = int.from_bytes(partner_pokemon[0:2], "little")

            # TODO reconsider this???
            # just make a progressive partner
            if (
                partner_counts_as_party_slot == 7
                and partner not in self.allowed_partners
                and partner != 0
            ):
                # with open("debug_log.txt", "a") as f:
                #     f.write(
                #         f"[DEBUG] {partner_pokemon=}, {partner_counts_as_party_slot=}, {partner=}, {self.allowed_partners=}\n"
                #     )
                if len(self.allowed_partners) >= 1:
                    partner = 0x0FFF0000 | self.first_partner
                    default_partner = (0x0FFF00BC).to_bytes(4, "little")

                    await bizhawk.write(
                        ctx.bizhawk_ctx,
                        [
                            (
                                data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first,
                                default_partner,
                                "ARM9 System Bus",
                            )
                        ],
                    )
                else:
                    """Experimental feature!!!"""
                    await bizhawk.write(
                        ctx.bizhawk_ctx,
                        [
                            (
                                data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first,
                                (0).to_bytes(24, "little"),
                                "ARM9 System Bus",
                            )
                        ],
                    )

            game_clear = False
            local_checked_locations: Set[int] = set()

            for browser_number, species in data.species.items():
                offset = species.browser_offset

                if not (0 <= offset < len(browser_captures_bytes)):
                    continue

                byte_value = browser_captures_bytes[offset]
                if ((byte_value >> species.browser_flag) & 1) != 0:
                    location_id = location_category_to_id(
                        species.browser_id, LocationCategory.BROWSER
                    )

                    if species.browser_id in ctx.slot_data["blacklisted_captures"]:
                        continue
                    local_checked_locations.add(location_id)

            local_captured_pokemon = len(local_checked_locations)
            target = ctx.slot_data["capture_count_target"]
            # if local_captured_pokemon >= target:
            #     game_clear = True

            quests_checked: Set[int] = set()
            alternate_quests: Set[int] = set()
            for i, byte in enumerate(quest_bytes, start=1):
                if not (0 < i < 61):
                    continue

                if not (byte & 0b00000010):
                    continue

                index = None
                if 41 <= i <= 43:
                    alternate_quests.add(i)
                elif i > 43:
                    index = i - 1
                else:
                    index = i

                location_id = location_category_to_id(index, LocationCategory.QUEST)
                quests_checked.add(location_id)

            alternate_to_actual = set(
                (
                    location_category_to_id(41, LocationCategory.QUEST),
                    location_category_to_id(42, LocationCategory.QUEST),
                )[: len(alternate_quests)]
            )
            quests_checked |= alternate_to_actual

            local_checked_locations |= quests_checked
            if local_checked_locations != self.local_checked_locations:
                self.local_checked_locations = local_checked_locations

                if local_checked_locations is not None:
                    await ctx.check_locations(local_checked_locations)

            if not ctx.finished_game and game_clear:
                ctx.finished_game = True
                await ctx.send_msgs(
                    [
                        {
                            "cmd": "StatusUpdate",
                            "status": ClientStatus.CLIENT_GOAL,
                        }
                    ]
                )

            if num_receieved_items < len(ctx.items_received):
                await self.handle_received_items(ctx, guards, num_receieved_items)

        except bizhawk.RequestFailedError:
            # Exit handler and return to main loop to reconnect
            pass

    async def handle_tracker_info(
        self, ctx: "BizHawkClientContext", guards: Dict[str, Tuple[int, bytes, str]]
    ) -> None:
        # TODO Current map
        ...

    async def handle_death_link(
        self, ctx: "BizHawkClientContext", guards: Dict[str, Tuple[int, bytes, str]]
    ) -> None:
        if ctx.slot_data.get("death_link", Toggle.option_false) != Toggle.option_true:
            return
        return

        if "DeathLink" not in ctx.tags:
            await ctx.update_death_link(True)
            self.previous_death_link = ctx.last_death_link

        read_result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (data.ram_addresses["CURRENT_HEALTH"].first, 1, "ARM9 System Bus"),
            ],
        )  # combat health uses a different memory address, find this.
        #

        current_hp = read_result[0][0]

        if current_hp is None:
            return

        if current_hp == 0:
            pass

    async def handle_received_items(
        self,
        ctx: "BizHawkClientContext",
        guards: Dict[str, Tuple[int, bytes, str]],
        num_receieved_items: int,
    ) -> None:

        next_item = ctx.items_received[num_receieved_items]
        item = data.items[items.reverse_offset_item_value(next_item.item)]

        writes = []
        if ItemCategory.STYLER_UPGRADE in item.item_categories:
            val = await self.handle_styler_upgrade(
                ctx,
                item,
                next_item.item,
            )
            writes.extend(val)

        elif ItemCategory.PLAYER_ATTRIBUTES in item.item_categories:
            val = await self.handle_player_attributes(ctx, item, next_item.item)
            writes.extend(val)

        elif ItemCategory.PARTNER in item.item_categories:
            val = await self.handle_give_partner_pokemon(ctx, item, next_item.item)
            writes.extend(val)

        elif ItemCategory.FIELD_MOVE in item.item_categories:
            val = await self.handle_give_field_move(ctx, item, next_item.item)
            writes.extend(val)

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                *writes,
                (
                    data.ram_addresses["RECEIVED_ITEM_ADDRESS"].first,
                    (num_receieved_items + 1).to_bytes(3, "little"),
                    "ARM9 System Bus",
                ),
            ],
        )

    async def handle_styler_upgrade(
        self,
        ctx: "BizHawkClientContext",
        item: ItemData,
        item_id: int,
    ) -> List:
        writes = []

        if item.label == "Supreme Defense" or item.bit_offset is None:
            # TODO, have it check all defenses and increase them by one
            # if they're already at 2 ;.;.
            return []

        byte_index = item.bit_offset // 8
        bit = item.bit_offset % 8

        read_result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (
                    data.ram_addresses["STYLUS_UPGRADE_TABLE_ADDRESS"].first
                    + byte_index,
                    1,
                    "ARM9 System Bus",
                )
            ],
        )

        current_byte = read_result[0] if read_result else 0
        current_byte = int.from_bytes(current_byte, "little")

        level_from_inventory = 0
        defense = False

        for all_item in ctx.items_received:
            if all_item.item == item_id:
                level_from_inventory += 1
                continue
            elif (
                data.items[items.reverse_offset_item_value(all_item.item)].label
                == "Supreme Defense"
            ):
                defense = True
        level_from_inventory = min(level_from_inventory, item.copies)
        if level_from_inventory < 2:
            new_value = level_from_inventory
        else:
            new_value = 3 if defense else 2

        mask = 0b11 << bit

        new_byte = (current_byte & ~mask) | ((new_value & 0b11) << bit)

        if item.label == "Energy Plus":
            # TODO, move towards end and have increment HP, else this will only
            # apply at next level up.
            self.has_energy_plus = True

            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (
                        data.ram_addresses["CURRENT_HEALTH"].first,
                        1,
                        "ARM9 System Bus",
                    ),
                    (data.ram_addresses["MAX_HEALTH"].first, 1, "ARM9 System Bus"),
                ],
            )

            current_hp = int.from_bytes(read_result[0], "little")
            max_hp = int.from_bytes(read_result[1], "little")

            writes += [
                (
                    data.ram_addresses["CURRENT_HEALTH"].first,
                    bytes([current_hp + 5]),
                    "ARM9 System Bus",
                ),
                (
                    data.ram_addresses["MAX_HEALTH"].first,
                    bytes([max_hp + 5]),
                    "ARM9 System Bus",
                ),
            ]

        writes += [
            (
                data.ram_addresses["STYLUS_UPGRADE_TABLE_ADDRESS"].first + byte_index,
                bytes([new_byte]),
                "ARM9 System Bus",
            )
        ]

        return writes

    async def handle_player_attributes(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        count = sum(1 for it in ctx.items_received if it.item == item_id)

        if item.label in ["Progressive Styler", "Progressive Rank"]:
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (
                        data.ram_addresses["CURRENT_STYLER_AND_RANK"].first,
                        1,
                        "ARM9 System Bus",
                    )
                ],
            )
            styler_and_rank = int.from_bytes(read_result[0], "little")

            if item.label == "Progressive Rank":
                rank = min(count * ctx.slot_data["rank_up_increment"], 10)
                new_value = (styler_and_rank & 0xF0) | (rank & 0x0F)

            elif item.label == "Progressive Styler":
                styler = min(2, count)  # Figure out if there are only 2 styler models
                self.styler_model = styler
                new_value = (styler_and_rank & 0x0F) | (styler << 4)
            else:
                return []

            return [
                (
                    data.ram_addresses["CURRENT_STYLER_AND_RANK"].first,
                    bytes([new_value]),
                    "ARM9 System Bus",
                )
            ]

        level = min(1 + (ctx.slot_data["level_up_increment"] * count), 99)

        writes = []
        if item.label in ["Progressive Power", "Progressive Attributes"]:
            writes.append(
                (
                    data.ram_addresses["STYLUS_LEVEL"].first,
                    bytes([level]),
                    "ARM9 System Bus",
                )
            )
        if item.label in ["Progressive Energy", "Progressive Attributes"]:
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (
                        data.ram_addresses["CURRENT_HEALTH"].first,
                        1,
                        "ARM9 System Bus",
                    ),
                    (data.ram_addresses["MAX_HEALTH"].first, 1, "ARM9 System Bus"),
                ],
            )
            if count == 1:
                prev_level = 1
            else:
                prev_level = min(
                    1 + (ctx.slot_data["level_up_increment"] * (count - 1)), 99
                )

            current_hp = int.from_bytes(read_result[0], "little")
            max_hp = int.from_bytes(read_result[1], "little")

            increase = data.styler_levels[level][0] - data.styler_levels[prev_level][0]
            if data.styler_levels[prev_level][0] == max_hp and self.has_energy_plus:
                increase += 5

            writes += [
                (
                    data.ram_addresses["CURRENT_HEALTH"].first,
                    bytes([current_hp + increase]),
                    "ARM9 System Bus",
                ),
                (
                    data.ram_addresses["MAX_HEALTH"].first,
                    bytes([max_hp + increase]),
                    "ARM9 System Bus",
                ),
            ]

        return writes

    async def handle_give_partner_pokemon(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        item_type, pokemon_name = item.label.split(" - ")

        pokemon = None
        for p in data.species.values():
            if p.name == pokemon_name:
                pokemon = p
                break
        self.allowed_partners += list(pokemon.species_ids)
        # currently I just add al HOWEVER not all forms should be possible
        # as partner vanilla. unless we randomize or set partners randomly this is not an issue.

        byte_offset = item.bit_offset // 8
        result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (
                    data.ram_addresses["PARTNER_POKEMON_TABLE_ADDRESS"].first
                    + byte_offset,
                    1,
                    "ARM9 System Bus",
                )
            ],
        )
        current = result[0][0]
        bit = item.bit_offset % 8

        new_value = current | (0b1 << bit)

        writes = [
            (
                data.ram_addresses["PARTNER_POKEMON_TABLE_ADDRESS"].first + byte_offset,
                new_value.to_bytes(1, "little"),
                "ARM9 System Bus",
            )
        ]
        return writes

    async def handle_give_field_move(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        writes = []

        field_move = item.item_id % 100
        for pok in data.species.values():
            if pok.field_move.category != field_move:
                continue
            for row in pok.poke_id_indexes:

                writes += [
                    (
                        data.ram_addresses["POKE_ID_TABLE_ADDRESS"].first
                        + row * POKE_ID_ROW_RAM_SIZE
                        + 5,
                        field_move.to_bytes(1, "little"),
                        "ARM9 System Bus",
                    )
                ]
        return writes

    async def patch_level_up_instructions(self, ctx: "BizHawkClientContext"):
        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                # (
                #     data.ram_addresses["INSTRUCTION_LEVEL_UP_STYLER_LEVEL_UP"].first,
                #     NOP_INSTRUCTION_BYTES,
                #     "ARM9 System Bus",
                # ),
                # (
                #     data.ram_addresses["INSTRUCTION_LEVEL_UP_MAX_HEALTH_UP"].first,
                #     NOP_INSTRUCTION_BYTES,
                #     "ARM9 System Bus",
                # ),
                (
                    data.ram_addresses["INSTRUCTION_LEVEL_UP_HEALTH_UP"].first,
                    NOP_INSTRUCTION_BYTES,
                    "ARM9 System Bus",
                ),
            ],
        )
