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

from .data import data, BROWSER_START_ADDRESS, ItemCategory, ItemData, GameStateEnum
from . import items, options

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

RECEIVED_ITEM_ADDRESS = data.ram_addresses["RECEIVED_ITEM_ADDRESS"]


class PokemonRangerSOA(BizHawkClient):
    game = "PokemonRangerSOA"
    system = "NDS"
    patch_suffix = None

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

    level_up_patched: bool

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
            num_receieved_items = 0

            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (data.ram_addresses["GAME_STATE"].address, 1, "ARM9 System Bus"),
                    (BROWSER_START_ADDRESS, 0x7A, "ARM9 System Bus"),
                    (RECEIVED_ITEM_ADDRESS.address, 3, "ARM9 System Bus"),
                ],
            )

            if read_result is not None:
                game_state = int.from_bytes(read_result[0], "little")
                browser_captures_bytes = read_result[1]
                num_receieved_items = int.from_bytes(read_result[2], "little")

            if (
                ctx.slot_data["level_up_type"] != options.LevelUpType.option_vanilla
                and game_state == GameStateEnum.BATTLE
            ):
                if not self.level_up_patched:
                    # await self.patch_level_up_instructions(ctx)
                    self.level_up_patched = True
                return
            else:
                self.level_up_patched = False

            """
            BEING IN BATTLE WILL STOP THINGS BELOW OCCURRING!
            AT THE MOMENT THE SOMETHING IS LAGGY, THIS IS TO REDUCE
            LAG IN COMBAT.
            """

            if num_receieved_items < len(ctx.items_received):
                await self.handle_received_items(ctx, guards, num_receieved_items)

            game_clear = False
            local_checked_locations: set[int] = set()

            for browser_number, species in data.species.items():
                offset = species.browser_offset

                if not (0 <= offset < len(browser_captures_bytes)):
                    continue

                byte_value = browser_captures_bytes[offset]
                if ((byte_value >> species.browser_flag) & 1) != 0:
                    location_id = species.browser_id

                    if location_id in ctx.slot_data["blacklisted_captures"]:
                        continue
                    local_checked_locations.add(location_id)

            local_captured_pokemon = len(local_checked_locations)
            target = ctx.slot_data["capture_count_target"]
            if local_captured_pokemon >= target:
                game_clear = True

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
        # TODO
        if ctx.slot_data.get("death_link", Toggle.option_false) != Toggle.option_true:
            return

        if "DeathLink" not in ctx.tags:
            await ctx.update_death_link(True)
            self.previous_death_link = ctx.last_death_link

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

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                *writes,
                (
                    data.ram_addresses["RECEIVED_ITEM_ADDRESS"].address,
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
                    data.ram_addresses["STYLUS_UPGRADE_TABLE_ADDRESS"].address
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
                        data.ram_addresses["CURRENT_HEALTH"].address,
                        1,
                        "ARM9 System Bus",
                    ),
                    (data.ram_addresses["MAX_HEALTH"].address, 1, "ARM9 System Bus"),
                ],
            )

            current_hp = int.from_bytes(read_result[0], "little")
            max_hp = int.from_bytes(read_result[1], "little")

            writes += [
                (
                    data.ram_addresses["CURRENT_HEALTH"].address,
                    bytes([current_hp + 5]),
                    "ARM9 System Bus",
                ),
                (
                    data.ram_addresses["MAX_HEALTH"].address,
                    bytes([max_hp + 5]),
                    "ARM9 System Bus",
                ),
            ]

        writes += [
            (
                data.ram_addresses["STYLUS_UPGRADE_TABLE_ADDRESS"].address + byte_index,
                bytes([new_byte]),
                "ARM9 System Bus",
            )
        ]

        return writes

    async def handle_player_attributes(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        count = sum(1 for it in ctx.items_received if it.item == item_id)

        if item.label == "Progressive Rank":
            rank = min(count * ctx.slot_data["rank_up_increment"], 10)

            return [
                (
                    data.ram_addresses["CURRENT_RANK"].address,
                    bytes([rank]),
                    "ARM9 System Bus",
                )
            ]

        level = min(1 + (ctx.slot_data["level_up_increment"] * count), 99)

        writes = []
        if item.label in ["Progressive Power", "Progressive Attributes"]:
            writes.append(
                (
                    data.ram_addresses["STYLUS_LEVEL"].address,
                    bytes([level]),
                    "ARM9 System Bus",
                )
            )
        if item.label in ["Progressive Energy", "Progressive Attributes"]:
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (
                        data.ram_addresses["CURRENT_HEALTH"].address,
                        1,
                        "ARM9 System Bus",
                    ),
                    (data.ram_addresses["MAX_HEALTH"].address, 1, "ARM9 System Bus"),
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

            with open("debug_log.txt", "a") as f:
                f.write(
                    f"[DEBUG] {current_hp=}, {max_hp=}, {increase}, {level=}, {prev_level}, {count=}, \n"
                    f"{self.has_energy_plus=}, {data.styler_levels[level][0]=}, {data.styler_levels[prev_level][0]=}\n\n"
                )

            writes += [
                (
                    data.ram_addresses["CURRENT_HEALTH"].address,
                    bytes([current_hp + increase]),
                    "ARM9 System Bus",
                ),
                (
                    data.ram_addresses["MAX_HEALTH"].address,
                    bytes([max_hp + increase]),
                    "ARM9 System Bus",
                ),
            ]

        return writes

    async def patch_level_up_instructions(self, ctx: "BizHawkClientContext"):
        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                (
                    data.ram_addresses["INSTRUCTION_LEVEL_UP_STYLER_LEVEL_UP"].address,
                    bytes.fromhex("0000A0E3"),
                    "ARM9 System Bus",
                ),
                (
                    data.ram_addresses["INSTRUCTION_LEVEL_UP_MAX_HEALTH_UP"].address,
                    bytes.fromhex("0000A0E3"),
                    "ARM9 System Bus",
                ),
                (
                    data.ram_addresses["INSTRUCTION_LEVEL_UP_HEALTH_UP"].address,
                    bytes.fromhex("0000A0E3"),
                    "ARM9 System Bus",
                ),
            ],
        )
