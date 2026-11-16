import asyncio
import copy
import orjson
import random
import time
from typing import TYPE_CHECKING, Optional, Dict, Set, Tuple, List, Any
import uuid

from NetUtils import ClientStatus
from Options import Toggle
import Utils
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from worlds._bizhawk.client import BizHawkClient

from .data import (
    data,
    ItemData,
    GameStateEnum,
    LocationCategory,
    location_category_to_id,
    FieldMoveCategory,
    POKE_ID_ROW_RAM_SIZE,
    VANILLA_PARTNERS_FORMS_UNLOCK_ORDER,
)
from . import items, options
from .data_dir.items import ItemCategory
from .items import offset_item_value
from .options import PokemonRSOADeathLink, RankUpItem, StylerModelItem

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

RECEIVED_ITEM_ADDRESS = data.ram_addresses["RECEIVED_ITEM_ADDRESS"]
NOP_INSTRUCTION_BYTES = bytes.fromhex("0000A0E3")


class PokemonRangerSOA(BizHawkClient):
    game = "Pokemon Ranger Shadows of Almia"
    system = "NDS"
    patch_suffix = ".apprsoa"

    ram = "ARM9 System Bus"

    local_checked_locations: Set[int]

    death_counter: Optional[int]
    previous_death_link: float
    ignore_next_death_link: int

    current_map_id: Optional[int]

    level: int
    energy: int
    has_energy_plus: bool
    styler_model: int

    battle_patched: bool
    item_info: Dict[str, Any]

    first_partner = Optional[int]

    def initialize_client(self):
        self.local_checked_locations = set()
        self.death_counter = None
        self.previous_death_link = 0
        self.ignore_next_death_link = 0
        self.current_map_id = None
        self.battle_patched = False
        self.item_info = {}
        self.has_energy_plus = False
        self.styler_model = 0
        self.first_partner = None

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        header = await bizhawk.read(ctx.bizhawk_ctx, ((0x00000000, 0x10, "ROM"),))

        raw = bytes(header[0])
        if not raw.startswith(b"POKE RANGER2YP2E"):
            return False

        ctx.game = self.game
        ctx.items_handling = 0b111
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.125

        self.initialize_client()

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None:
            return

        try:
            # with open("debug_log.txt", "a") as f:
            #     f.write(f"[DEBUG] {ctx.slot_data["field_move_stages"]}\n")

            guards: Dict[str, Tuple[int, bytes, str]] = {}

            await self.handle_tracker_info(ctx, guards)
            await self.handle_death_link(ctx, guards)

            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (data.ram_addresses["GAME_STATE"].first, 1, self.ram),
                    (
                        data.ram_addresses["BROWSER_TABLE_ADDRESS"].first,
                        0x7A,
                        self.ram,
                    ),
                    (RECEIVED_ITEM_ADDRESS.first, 3, self.ram),
                    (data.ram_addresses["CURRENT_STYLER_AND_RANK"].first, 1, self.ram),
                    (data.ram_addresses["CURRENT_MISSION"].first, 3, self.ram),
                    (data.ram_addresses["CURRENT_ROOM_ID"].first, 2, self.ram),
                    (data.ram_addresses["QUEST_TABLE_ADDRESS"].first, 60, self.ram),
                    (data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first, 10, self.ram),
                ],
            )

            if read_result is None:
                return
            game_state = int.from_bytes(read_result[0], "little")
            browser_captures_bytes = read_result[1]
            num_receieved_items = int.from_bytes(read_result[2], "little")
            styler_and_rank = int.from_bytes(read_result[3], "little")
            current_mission = read_result[4][0]
            last_mission_id = read_result[4][2]
            room_id = int.from_bytes(read_result[5], "little")
            quest_bytes = read_result[6]
            partner_pokemon = read_result[7]

            if game_state == 1 and not self.battle_patched:
                writes = []
                if self.item_info.get("vatonage"):
                    writes += [(0x0212B950, [0xA0], self.ram)]

                await bizhawk.write(ctx.bizhawk_ctx, writes)
                self.battle_patched = True
            elif game_state != 1:
                self.battle_patched = False

            game_clear = False
            local_checked_locations: Set[int] = set()

            local_captures: Set[int] = set()
            for browser_number, species in data.species.items():
                offset = species.browser_offset

                if not (0 <= offset < len(browser_captures_bytes)):
                    continue

                byte_value = browser_captures_bytes[offset]
                if ((byte_value >> species.browser_flag) & 1) != 0:
                    location_id = location_category_to_id(
                        species.browser_id, LocationCategory.BROWSER
                    )

                    # if species.browser_id in ctx.slot_data["blacklisted_captures"]:
                    #     continue  # TODO figure out if this should be done at all
                    #  blacklisting should be respected during gen, so if you can catch
                    #  it it's fair game
                    local_captures.add(location_id)

            local_checked_locations |= local_captures
            del local_captures

            mission_checked: Set[int] = set()
            last_mission = 0
            if last_mission_id == 33:
                mission_checked.add(
                    location_category_to_id(0, LocationCategory.MISSION)
                )
            elif last_mission_id:
                for i in range(min(last_mission_id + 1, 17)):
                    mission_checked.add(
                        location_category_to_id(i, LocationCategory.MISSION)
                    )
            local_checked_locations |= mission_checked

            quests_checked: Set[int] = set()
            alternate_quests: Set[int] = set()
            for i, byte in enumerate(quest_bytes, start=1):
                if not (0 < i < 61):
                    continue

                if not (byte & 0b00000010):
                    continue

                if 41 <= i <= 43:
                    alternate_quests.add(i)
                    continue  # TODO tesing, but makes sense!
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
            del quests_checked

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
        if (
            ctx.slot_data.get("death_link", PokemonRSOADeathLink.option_false)
            == PokemonRSOADeathLink.option_false
        ):
            return

        if "DeathLink" not in ctx.tags:
            await ctx.update_death_link(True)
            self.previous_death_link = ctx.last_death_link

        read_result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (data.ram_addresses["CURRENT_HEALTH"].first, 2, self.ram),
                (data.ram_addresses["GAME_STATE"].first, 1, self.ram),
                (data.ram_addresses["CUR_SCENE"].first, 4, self.ram),
            ],
        )

        if read_result is None:
            return

        current_hp = read_result[0][0]
        max_hp = read_result[0][1]
        game_state = read_result[1][0]
        cur_scene = int.from_bytes(read_result[2], "little")

        hp_address = data.ram_addresses["CURRENT_HEALTH"].first

        if game_state == GameStateEnum.FLUSHING and self.ignore_next_death_link:
            return  # otherwise the hp reset is consumed :(
        if game_state in (
            GameStateEnum.INTRO_SCREEN,
            GameStateEnum.TITLE_SCREEN,
            GameStateEnum.RESUME_GAME,
        ):
            self.previous_death_link = ctx.last_death_link
            if self.ignore_next_death_link == 2:
                self.ignore_next_death_link = 1
            return

        if game_state == GameStateEnum.BATTLE:
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx, [(cur_scene + 0xD8, 4, self.ram)]
            )
            hp_address2 = int.from_bytes(read_result[0], "little") + 0x19C
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx, [(hp_address2, 1, self.ram)]
            )
            if read_result is None:
                return  # just try again next time
            current_hp = read_result[0][0]

        if current_hp == 0:
            if self.ignore_next_death_link:
                self.previous_death_link = ctx.last_death_link
                return
            if game_state == GameStateEnum.BATTLE:
                text = f"{ctx.player_names[ctx.slot]} died in battle"
            else:
                text = f"{ctx.player_names[ctx.slot]} died walking around"

            await ctx.send_death(text)
            self.ignore_next_death_link = 2
            return

        # if current_hp != 0:
        if self.ignore_next_death_link:
            if self.ignore_next_death_link == 2:
                return
            self.ignore_next_death_link = 0
            if (
                ctx.slot_data.get("death_link")
                != PokemonRSOADeathLink.option_true_max_energy_on_death
            ):
                return
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (data.ram_addresses["CURRENT_HEALTH"].first, [max_hp], self.ram),
                ],
            )
            return
        if self.previous_death_link == ctx.last_death_link:
            return

        self.previous_death_link = ctx.last_death_link

        death_link_damage = ctx.slot_data["death_link_damage"]
        new_hp = max(0, current_hp - max(1, int(max_hp * death_link_damage / 100)))
        base_write = [(hp_address, [new_hp], self.ram)]
        guard = []
        if game_state == GameStateEnum.BATTLE:
            base_write += [(hp_address2, [new_hp], self.ram)]
            guard += [(data.ram_addresses["GAME_STATE"].first, [game_state], self.ram)]
        succeeded = await bizhawk.guarded_write(
            ctx.bizhawk_ctx,
            base_write,
            guard,
        )
        if not succeeded:
            self.previous_death_link -= 1
            return
        if new_hp == 0:
            self.ignore_next_death_link = 2
        return

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

            if (
                item.label == "Progressive Rank"
                and ctx.slot_data["rank_up_item"] != RankUpItem.option_vanilla
            ):
                if ctx.slot_data["rank_up_item"] == RankUpItem.option_item:
                    ranks = {1: 4, 2: 6, 3: 8, 4: 10}
                    rank = ranks.get(count, 10)
                else:
                    rank = min(count, 10)
                new_value = (styler_and_rank & 0xF0) | (rank & 0x0F)

            elif (
                item.label == "Progressive Styler"
                and ctx.slot_data["rank_up_item"] != StylerModelItem.option_vanilla
            ):
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
        if item.label in ["Progressive Power", "Progressive Level"]:
            writes.append(
                (
                    data.ram_addresses["STYLUS_LEVEL"].first,
                    bytes([level]),
                    "ARM9 System Bus",
                )
            )
        if item.label in ["Progressive Energy", "Progressive Level"]:
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
        form_id = items.reverse_offset_item_value(item_id - 100)

        mapping = {
            164: 1,
            167: 2,
            161: 3,
            188: 4,
            152: 5,
            31: 6,  # machop
            220: 7,
            217: 8,  # hippo
            210: 10,
            175: 11,
            182: 12,
            92: 13,
            213: 14,
            99: 15,
            183: 16,
            #  TODO add munchlax and starly, those dont work well cuz of some flag
        }  # this order is dangerous ;.;

        bit_offsets = []
        if not ctx.slot_data.get("randomize_partners", False):
            bit_offset = mapping.get(form_id, None)
            if bit_offset is None:
                return []
            bit_offsets.append(bit_offset)
        else:
            forms = ctx.slot_data["modified_partners"]
            if form_id not in forms:
                return []
            received = sum(1 for it in ctx.items_received if it.item == item_id)
            forms = forms[3:] + forms[:3]
            for i, form in enumerate(forms):
                if form == form_id:
                    bit_offsets.append(
                        mapping.get(VANILLA_PARTNERS_FORMS_UNLOCK_ORDER[i])
                    )
                    if len(bit_offsets) >= received:
                        break

        result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [(data.ram_addresses["PARTNER_POKEMON_TABLE_ADDRESS"].first, 2, self.ram)],
        )
        result = list(result[0])

        for bit_offset in bit_offsets:
            byte_offset = bit_offset // 8
            bit = bit_offset % 8

            result[byte_offset] |= 0b1 << bit

        writes = [
            (
                data.ram_addresses["PARTNER_POKEMON_TABLE_ADDRESS"].first,
                result,
                "ARM9 System Bus",
            )
        ]
        return writes

    async def handle_give_field_move(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        writes = []
        received = sum(1 for it in ctx.items_received if it.item == item_id)

        field_move = item.item_id % 100  # technically correct ...
        levels = ctx.slot_data["field_move_stages"].get(str(field_move), None)
        if levels is None or received > len(levels):
            level = 5
        else:
            level = levels[received - 1]
        for pok in data.species.values():
            if pok.field_move.category != field_move:
                continue
            if pok.field_move.level > level:
                continue
            for row in pok.forms.keys():
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
