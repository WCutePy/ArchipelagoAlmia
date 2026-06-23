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

from . import items, options, data

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext


NOP_INSTRUCTION_BYTES = bytes.fromhex("0000A0E3")
STAGE_UNLOCK_LOCATION = 0x02122BC5
RECEIVED_ITEMS_LOCATION = 0x021222D6  # Currently some address
                                      # for the players endless best score


def stage_id_to_location_id(num: int) -> int:
    return 1 + len(data.stages[0].location_names) * num


class PokemonTrozeiCient(BizHawkClient):
    game = "Pokemon Trozei"
    system = "NDS"
    patch_suffix = (".apptrozei", ".applink")

    ram_read_write_domain = "ARM9 System Bus"
    rom_read_only_domain = "ROM"

    local_checked_locations: Set[int]
    local_unlocked_stages: Set[int]
    local_found_key_items: Dict[str, bool]

    goal_flag: Optional[int]

    death_counter: Optional[int]
    previous_death_link: float
    ignore_next_death_link: bool

    in_stage: bool

    def initialize_client(self, ctx: "BizHawkClientContext"):
        self.local_checked_locations = set()
        self.local_found_key_items = {}
        self.local_unlocked_stages = set()

        for item in ctx.items_received:
            item_id = item.item
            if item_id < 100:
                self.local_unlocked_stages.add(item_id - 1)

        self.goal_flag = None

        self.death_counter = None
        self.previous_death_link = 0
        self.ignore_next_death_link = False

        self.in_stage = True


    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        header = await bizhawk.read(
            ctx.bizhawk_ctx,
            (
                (0x00000000, 0x0B, self.rom_read_only_domain),
            )
        )

        raw = bytes(header[0])
        if not raw.startswith(b"POKEMONLINK"):
            return False

        ctx.game = self.game
        ctx.items_handling = 0b111
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.125

        self.initialize_client(ctx)

        # await bizhawk.write(
        #     ctx.bizhawk_ctx,
        #     [
        #         (
        #             RECEIVED_ITEMS_LOCATION,
        #             (0).to_bytes(4, "little", signed=False),
        #             self.ram_read_write_domain
        #         )
        #     ]
        # )

        endless_score = await bizhawk.read(
            ctx.bizhawk_ctx,
            (
                (0x021222D5, 5, self.ram_read_write_domain),
            )
        )
        buf = bytearray(endless_score[0])
        if not ((buf[3] >= 0xE0) and (buf[4] & 0x01) == 1):
            buf[0] &= 0b111
            buf[1] = 0x00
            buf[2] = 0x00
            buf[3] = 0xE0
            buf[4] |= 0x01

            await bizhawk.write(
                ctx.bizhawk_ctx,
                (
                    (0x021222D5, bytes(buf), self.ram_read_write_domain),
                )
            )
        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None:
            return


        try:
            guards: Dict[str, Tuple[int, bytes, str]] = {}

            # await self.handle_tracker_info(ctx, guards)
            # await self.handle_death_link(ctx, guards)

            in_stage = None

            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (0x022101DC, 1, self.ram_read_write_domain),
                    (STAGE_UNLOCK_LOCATION, 12, self.ram_read_write_domain),
                    (RECEIVED_ITEMS_LOCATION, 2, self.ram_read_write_domain),
                ],
            )

            in_stage = read_result[0][0]
            if in_stage == 0x00 and self.in_stage:
                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (0x020135C0, NOP_INSTRUCTION_BYTES, self.ram_read_write_domain)
                    ]
                )
                self.in_stage = False
            elif in_stage == 0x01 and not self.in_stage:
                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (0x020135C0, bytes.fromhex("002185E7"), self.ram_read_write_domain)
                    ]
                )
                self.in_stage = True

            locations = read_result[1]
            game_clear = False
            local_checked_locations: Set[int] = set()

            for i, stage in enumerate(data.stages):
                byte = i // 4
                index = i % 4

                bit1 = 1 + index * 2

                value1 = (locations[byte] >> bit1) & 1

                if bit1 == 7:
                    value2 = locations[byte + 1] & 1
                else:
                    value2 = (locations[byte] >> (bit1 + 1)) & 1

                pair = value1 | (value2 << 1)

                is_unlocked = pair != 0b00
                is_completed = pair == 0b11

                if is_unlocked and i not in self.local_unlocked_stages:
                    await self.write_stage_location(ctx, locations[byte:byte+2], byte, bit1, 0b00)
                    continue

                if is_completed:
                    num = stage_id_to_location_id(i)
                    local_checked_locations.add(num)
                    local_checked_locations.add(num + 1)

            loc_8 = locations[8]
            loc_9 = locations[9]  # top left
            loc_10 = locations[10]  # top right and bottom left
            loc_11 = locations[11]  # bottom right
            if stage_id_to_location_id(30) in ctx.checked_locations:
                if not (loc_11 >> 1) & 1:
                    loc_11 |= 0b10  # access top right
                    loc_10 |= 0b11  # access top left and bottom right
                    loc_9 |= 0b1000  # access top right
            if stage_id_to_location_id(32) in ctx.checked_locations:
                if not loc_11 & 1:
                    loc_11 |= 0b01  # access bottom left
                    loc_10 |= 0b110000  # access bottom left and top left
                    loc_9 |= 0b1000000  # access bottom left


            if 35 in self.local_unlocked_stages and \
                    sum(stage_id_to_location_id(i) in ctx.checked_locations
                        for i in range(30, 35)) >= ctx.slot_data["required_bosses"]:

                if not (loc_8 & 0x80) and not (loc_9 & 0b1):
                    loc_9 |= 0b1

            if loc_11 != locations[11] or loc_9 != locations[9]:
                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (
                            STAGE_UNLOCK_LOCATION + 9,
                            bytes([loc_9, loc_10, loc_11]),
                            self.ram_read_write_domain,
                        )
                    ]
                )

            if local_checked_locations != self.local_checked_locations:
                self.local_checked_locations = local_checked_locations

                if local_checked_locations is not None:
                    await ctx.check_locations(local_checked_locations)

            if stage_id_to_location_id(35) in local_checked_locations:
                game_clear = True

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

            num_receieved_items = int.from_bytes(read_result[2], "little", signed=False)
            if num_receieved_items < len(ctx.items_received):
                await self.handle_received_items(ctx, guards, num_receieved_items)

        except bizhawk.RequestFailedError:
            pass


    async def write_stage_location(self, ctx: "BizHawkClientContext", locations: bytes, start_byte: int, bit1: int, value: int):
        value &= 0b11
        if bit1 == 7:
            byte1, byte2, *_ = locations

            byte1 = (byte1 & 0x7F) | ((value & 0b01) << 7)
            byte2 = (byte2 & 0xFE) | ((value >> 1) & 0b01)
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (
                        STAGE_UNLOCK_LOCATION + start_byte,
                        bytes([byte1]),
                        self.ram_read_write_domain
                    ),
                    (
                        STAGE_UNLOCK_LOCATION + start_byte + 1,
                        bytes([byte2]),
                        self.ram_read_write_domain
                    )
                ]
            )
        else:
            byte_value, *_ = locations

            mask = ~((1 << bit1) | (1 << (bit1 + 1))) & 0xFF
            byte_value = (byte_value & mask) | (value << bit1)

            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (
                        STAGE_UNLOCK_LOCATION + start_byte,
                        bytes([byte_value]),
                        self.ram_read_write_domain
                    )
                ]
            )

    async def handle_received_items(self, ctx: "BizHawkClientContext", guards: Dict[str, Tuple[int, bytes, str]], num_received_items: int):

        while num_received_items < len(ctx.items_received):
            item = ctx.items_received[num_received_items]
            item_id = item.item

            num_received_items += 1
            if item_id < 100:
                stage_id = item_id - 1
                byte = stage_id // 4
                bit1 = 1 + (stage_id % 4) * 2

                write = 0b01
                if stage_id * len(data.stages[0].location_names) + 1 in ctx.checked_locations:
                    write = 0b11

                if stage_id != 35 or stage_id == 35 and write == 0b11:
                    read_result = await bizhawk.read(
                        ctx.bizhawk_ctx,
                        [
                            (STAGE_UNLOCK_LOCATION + byte, 2, self.ram_read_write_domain),
                        ],
                    )
                    await self.write_stage_location(ctx, read_result[0], byte, bit1, write)
                self.local_unlocked_stages.add(stage_id)
            elif item_id < 103:
                read_result = await bizhawk.read(
                    ctx.bizhawk_ctx,
                    [
                        (0x02121e65, 1, self.ram_read_write_domain),
                    ],
                )
                new_val = int.from_bytes(read_result[0], "little", signed=False) + [1, 3, 5][item_id - 100]
                new_bytes = min(new_val, 255).to_bytes(1, "little", signed=False)

                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (
                            0x02121e65,
                            new_bytes,
                            self.ram_read_write_domain
                        )
                    ]
                )
            else:
                continue

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                (
                    RECEIVED_ITEMS_LOCATION,
                    num_received_items.to_bytes(2, "little", signed=False),
                    self.ram_read_write_domain
                )
            ]
        )

        return