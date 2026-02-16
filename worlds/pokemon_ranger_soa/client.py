import asyncio
import copy
import orjson
import random
import time
from typing import TYPE_CHECKING, Optional, Dict, Set, Tuple
import uuid

from NetUtils import ClientStatus
from Options import Toggle
import Utils
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from worlds._bizhawk.client import BizHawkClient

from .data import data, BROWSER_START_ADDRESS, ItemCategory, ItemData
from . import items

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


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
            await self.handle_received_items(ctx, guards)

            browser_captures_bytes = bytes(0)
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx, [(BROWSER_START_ADDRESS, 0x7A, "System Bus")]
            )
            if read_result is not None:
                browser_captures_bytes = read_result[0]

            game_clear = False
            local_checked_locations: set[int] = set()
            local_captured_pokemon = 0

            # with open("debug_log.txt", "a") as f:
            #     f.write(f"[DEBUG] browser: {browser_captures_bytes}\n")

            for browser_number, species in data.species.items():
                offset = species.browser_offset

                if not (0 <= offset < len(browser_captures_bytes)):
                    continue

                byte_value = browser_captures_bytes[offset]
                if ((byte_value >> species.browser_flag) & 1) != 0:
                    location_id = species.browser_id
                    #
                    # with open("debug_log.txt", "a") as f:
                    #     f.write(f"[DEBUG] {location_id=}\n{ctx.slot_data}\n\n")
                    if location_id in ctx.slot_data["blacklisted_captures"]:
                        continue
                    local_checked_locations.add(location_id)
                    local_captured_pokemon += 1

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
        self, ctx: "BizHawkClientContext", guards: Dict[str, Tuple[int, bytes, str]]
    ) -> None:

        received_item_address = data.ram_addresses["RECEIVED_ITEM_ADDRESS"]

        read_result = await bizhawk.guarded_read(
            ctx.bizhawk_ctx,
            [
                (received_item_address.address, 3, "System Bus"),
            ],
            [],
        )

        if read_result is None:
            return

        num_received_items = int.from_bytes(read_result[0], "little")

        if num_received_items >= len(ctx.items_received):
            return

        next_item = ctx.items_received[num_received_items]
        item = data.items[items.reverse_offset_item_value(next_item.item)]

        if ItemCategory.STYLER_UPGRADE in item.item_categories:
            await self.handle_styler_upgrade(
                ctx, item, next_item.item, num_received_items
            )
            return

    async def handle_styler_upgrade(
        self,
        ctx: "BizHawkClientContext",
        item: ItemData,
        item_id: int,
        num_items_received: int,
    ):
        if item.label == "Supreme Defense" or item.bit_offset is None:
            return

        byte_index = item.bit_offset // 8
        bit = item.bit_offset % 8

        read_result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (
                    data.ram_addresses["STYLUS_UPGRADE_TABLE_ADDRESS"].address
                    + byte_index,
                    1,
                    "System Bus",
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

        # with open("debug_log.txt", "a") as f:
        #     f.write(
        #         f"[DEBUG] {byte_index=}\n{item.item_id=}\n{new_byte=} {level_from_inventory=}\n"
        #     )

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                (
                    data.ram_addresses["STYLUS_UPGRADE_TABLE_ADDRESS"].address
                    + byte_index,
                    bytes([new_byte]),
                    "System Bus",
                ),
                (
                    data.ram_addresses["RECEIVED_ITEM_ADDRESS"].address,
                    (num_items_received + 1).to_bytes(3, "little"),
                    "System Bus",
                ),
            ],
        )
