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

from .data import data, BROWSER_START_ADDRESS

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
            if local_captured_pokemon >= 4:
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
