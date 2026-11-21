from collections import Counter
from typing import TYPE_CHECKING, Optional, Dict, Set, Tuple, List, Any

import worlds._bizhawk as bizhawk
from NetUtils import ClientStatus
from worlds._bizhawk.client import BizHawkClient
from . import items
from .data import (
    data,
    ItemData,
    GameStateEnum,
    LocationCategory,
    location_category_to_id,
    POKE_ID_ROW_RAM_SIZE,
    VANILLA_PARTNERS_FORMS_UNLOCK_ORDER,
    get_party_type,
    Party,
    ItemBase,
)
from .data_dir.items import ItemCategory
from .options import (
    PokemonRSOADeathLink,
    RankUpItem,
    StylerModelItem,
    LevelUpItem,
    GoalKeys,
)

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

RECEIVED_ITEM_ADDRESS = data.ram_addresses["RECEIVED_ITEM_ADDRESS"]
NOP_INSTRUCTION_BYTES = bytes.fromhex("0000A0E3")


"""
EMPTY SAVE LOCATIONS I USE

020BA2E4 - for level cap - pokemon bitflags

020BA302 - received items - idk anymore
"""


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
        ctx.watcher_timeout = 0.3

        self.initialize_client()

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None:
            return

        try:
            # with open("debug_log.txt", "a") as f:
            #     f.write(f"[DEBUG] {ctx.slot_data["field_move_stages"]}\n")

            guards: Dict[str, Tuple[int, bytes, str]] = {}

            """rework so it can be put lower?"""
            await self.handle_death_link(ctx, guards)
            if self.ignore_next_death_link:
                return

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
                    (data.ram_addresses["CURRENT_MISSION"].first, 3, self.ram),
                    (data.ram_addresses["SAVE_START"].first, 0x1C, self.ram),
                    (data.ram_addresses["QUEST_TABLE_ADDRESS"].first, 60, self.ram),
                    (
                        data.ram_addresses["POKE_ID_TABLE_ADDRESS"].first + 2,
                        1,
                        self.ram,
                    ),
                ],
            )

            if read_result is None:
                return
            game_state = int.from_bytes(read_result[0], "little")
            browser_captures_bytes = read_result[1]
            num_receieved_items = int.from_bytes(read_result[2], "little")
            current_mission = read_result[3][0]
            last_mission_id = read_result[3][2]
            room_id = int.from_bytes(read_result[4][0x1B:0x1D], "little")
            quest_bytes = read_result[5]
            game_reset = read_result[6][0] == 0

            if (
                game_state
                in [
                    GameStateEnum.TITLE_SCREEN,
                    GameStateEnum.INTRO_SCREEN,
                    GameStateEnum.RESUME_GAME,
                ]
                or read_result[4][2] == 0
            ):
                return
            if game_reset:
                await self.handle_rom_startup(ctx)
                return

            await self.handle_tracker_info(ctx, guards)

            if game_state == 1 and not self.battle_patched:
                writes = []
                if self.item_info.get("vatonage", False):
                    writes += [(0x0212B950, [0xA0], self.ram)]

                await bizhawk.write(ctx.bizhawk_ctx, writes)
                self.battle_patched = True
            elif game_state != 1:
                self.battle_patched = False

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
                    #  it it's fair game to send to the server
                    local_captures.add(location_id)

            local_checked_locations |= local_captures
            capture_count = len(local_captures)
            del local_captures

            mission_checked: Set[int] = set()
            last_mission = 0
            if last_mission_id == 33:
                mission_checked.add(
                    location_category_to_id(0, LocationCategory.MISSION)
                )
            elif last_mission_id:
                for i in range(min(last_mission_id + 1, 17)):
                    last_mission = i
                    mission_checked.add(
                        location_category_to_id(i, LocationCategory.MISSION)
                    )
            if last_mission >= 12:
                value = location_category_to_id(1, LocationCategory.EXTRA)
                mission_checked.add(value)
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

            if local_checked_locations != self.local_checked_locations:
                self.local_checked_locations = local_checked_locations

                if local_checked_locations is not None:
                    await ctx.check_locations(local_checked_locations)

            mission_goal_enabled = GoalKeys.mission in ctx.slot_data["goals"]
            mission_goal_achieved = (
                last_mission >= ctx.slot_data["mission_clear_target"]
            )
            quest_goal_enabled = GoalKeys.quest in ctx.slot_data["goals"]
            quest_goal_achieved = (
                len(quests_checked) >= ctx.slot_data["quest_clear_target"]
            )
            capture_goal_enabled = GoalKeys.capture in ctx.slot_data["goals"]
            capture_goal_achieved = (
                capture_count >= ctx.slot_data["capture_percent_target"]
            )

            if (
                (mission_goal_enabled or quest_goal_enabled or capture_goal_enabled)
                and (mission_goal_achieved or not mission_goal_enabled)
                and (quest_goal_achieved or not quest_goal_enabled)
                and (capture_goal_achieved or not capture_goal_enabled)
                and not ctx.finished_game
            ):
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
        except Exception as e:
            print(e)
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
                (data.ram_addresses["CURRENT_ROOM_ID"].first, 2, self.ram),
            ],
        )

        if read_result is None:
            return

        current_hp = read_result[0][0]
        max_hp = read_result[0][1]
        game_state = read_result[1][0]
        cur_scene = int.from_bytes(read_result[2], "little")
        room_id = int.from_bytes(read_result[3], "little")

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
                ctx.bizhawk_ctx,
                [(cur_scene + 0xD8, 4, self.ram), (0x0217B3E8 + 0x1444, 4, self.ram)],
            )
            hp_address2 = int.from_bytes(read_result[0], "little") + 0x19C
            battle_exports_ptr = int.from_bytes(read_result[1], "little")
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (hp_address2, 1, self.ram),
                    (battle_exports_ptr + 0x38, 0x20, self.ram),
                ],
            )
            if read_result is None:
                return  # just try again next time
            current_hp = read_result[0][0]

        if current_hp == 0:
            if self.ignore_next_death_link:
                self.previous_death_link = ctx.last_death_link
                return

            room = next(i for i in data.regions.values() if i.INDEX == room_id)
            if game_state == GameStateEnum.BATTLE:
                ids = Counter(
                    [
                        int.from_bytes(read_result[1][i : i + 4], "little")
                        for i in range(0, 0x20, 4)
                    ]
                )
                ids.pop(0, None)
                pokemon = [
                    (data.form_id_to_species[id_].name, c) for id_, c in ids.items()
                ]

                if len(pokemon) == 1 and pokemon[0][1] == 1:
                    mons = pokemon[0][0]
                else:
                    mons = ", ".join(f"{c} {name}" for name, c in pokemon)

                text = f"{ctx.player_names[ctx.slot]} died battling {mons} in {room.HUMAN_NAME}"
            else:
                movement = "walking"
                if get_party_type(room.map_id) == Party.OCEAN:
                    movement = "swimming"
                text = f"{ctx.player_names[ctx.slot]} died {movement} around {room.HUMAN_NAME}"

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

        for i in range(0, min(10, len(ctx.items_received) - num_receieved_items)):
            next_item = ctx.items_received[num_receieved_items]
            item = data.items[items.reverse_offset_item_value(next_item.item)]

            if ItemCategory.STYLER_UPGRADE in item.item_categories:
                val = await self.handle_styler_upgrade(ctx, item, next_item.item)
            elif ItemCategory.PLAYER_ATTRIBUTES in item.item_categories:
                val = await self.handle_player_attributes(ctx, item, next_item.item)
            elif ItemCategory.PARTNER in item.item_categories:
                val = await self.handle_give_partner_pokemon(ctx, item, next_item.item)
            elif ItemCategory.FIELD_MOVE in item.item_categories:
                val = await self.handle_give_field_move(ctx, item, next_item.item)
            elif ItemCategory.TRAP in item.item_categories:
                val = await self.handle_trap(ctx, item, next_item.item)
            elif ItemCategory.FILLER in item.item_categories:
                val = await self.handle_filler(ctx, item, next_item.item)
            else:
                continue

            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    *val,
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
        if item.item_id == 1006:
            self.item_info["vatonage"] = True
            return []

        count = sum(1 for it in ctx.items_received if it.item == item_id)

        if item.label in ["Progressive Styler", "Progressive Rank"]:
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (
                        data.ram_addresses["CURRENT_STYLER_AND_RANK"].first,
                        1,
                        self.ram,
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
                    self.ram,
                )
            ]

        increment = int(
            ctx.slot_data["level_up_max"] / ctx.slot_data["level_up_percent"]
        )
        level = min(1 + (increment * count), 99)

        writes = []
        level_up_item = ctx.slot_data["level_up_item"]
        if item.label in ["Progressive Power", "Progressive Level"] and level_up_item:
            writes += [
                (data.ram_addresses["LEVEL_CAP"].first, [level], self.ram),
            ]
            if (
                item.label == "Progressive Level"
                and level_up_item == LevelUpItem.option_level_cap
            ):
                return writes
            writes += [
                (
                    data.ram_addresses["STYLUS_LEVEL"].first,
                    bytes([level]),
                    self.ram,
                )
            ]
        if item.label in [
            "Progressive Energy",
            "Progressive Level",
        ] and level_up_item in [
            LevelUpItem.option_separate,
            LevelUpItem.option_together,
        ]:
            read_result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (data.ram_addresses["CURRENT_HEALTH"].first, 2, self.ram),
                ],
            )
            if count == 1:
                prev_level = 1
            else:
                prev_level = min(1 + (increment * (count - 1)), 99)

            current_hp = read_result[0][0]
            max_hp = read_result[0][1]

            increase = data.styler_levels[level][0] - data.styler_levels[prev_level][0]
            if data.styler_levels[prev_level][0] == max_hp and self.has_energy_plus:
                increase += 5

            writes += [
                (
                    data.ram_addresses["CURRENT_HEALTH"].first,
                    bytes([current_hp + increase, max_hp + increase]),
                    self.ram,
                ),
            ]

        return writes

    async def handle_give_partner_pokemon(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        form_id = items.reverse_offset_item_value(item.item_id - ItemBase.PARTNER)

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
                self.ram,
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
            min_level = 0
            max_level = 5
        else:
            if received == 1:
                min_level = 0
            else:
                min_level = levels[received - 2]
            max_level = levels[received - 1]
        for pok in data.species.values():
            if pok.field_move.category != field_move:
                continue
            if min_level > pok.field_move.level or max_level < pok.field_move.level:
                continue
            for row in pok.forms.keys():
                writes += [
                    (
                        data.ram_addresses["POKE_ID_TABLE_ADDRESS"].first
                        + row * POKE_ID_ROW_RAM_SIZE
                        + 5,
                        field_move.to_bytes(1, "little"),
                        self.ram,
                    )
                ]
        return writes

    async def handle_trap(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        base_id = item.item_id - 15000

        with open("debug_log.txt", "a") as f:
            f.write(f"[DEBUG] {item, base_id, item_id}\n")

        writes = []
        if base_id == 1:
            result = await bizhawk.read(
                ctx.bizhawk_ctx,
                [(data.ram_addresses["SAVE_START"].first, 1, self.ram)],
            )
            return [
                (
                    data.ram_addresses["SAVE_START"].first,
                    [(result[0][0] + 1) % 2],
                    self.ram,
                )
            ]
        elif ItemBase.PARTY_REPLACE < item.item_id < ItemBase.PARTY_REPLACE + 1000:
            return await self.give_mon(
                ctx, item.item_id - ItemBase.PARTY_REPLACE, to_all=True
            )
        return writes

    async def give_mon(self, ctx: "BizHawkClientContext", form_id: int, to_all=False):
        result = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first, 0xC2, self.ram),
                (
                    data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first + 0xF0,
                    0xC2,
                    self.ram,
                ),
                (data.ram_addresses["GAME_STATE"].first, 0x1, self.ram),
            ],
        )
        if result[2][0] == GameStateEnum.PARTY_SCREEN:
            """sadly can't give the pokemon in this screen"""
            return []
        new_bytes = form_id.to_bytes(2, "little")
        line = [new_bytes[0], new_bytes[1], 0, 0, 0, 0, 0, 0, 1]

        writes = []
        """I hate needing to account for partners
        I also hate that I want to fk over the sea too
        """
        for j in [0, 0xF0]:
            max_to = [0xC2, 0xC2 - 0x18]
            for i in range(0, max_to[j != 0], 0x18):
                if j == 0 and i == 0 and result[0][2] == 0xFF:
                    continue
                if j == 0 and result[0][2] != 0xFF and i == 0xC0:
                    break
                if not to_all and (
                    result[j != 0][i] != 0 or result[j != 0][1 + i] != 0
                ):
                    continue
                writes += [
                    (
                        data.ram_addresses["PARTNER_POKEMON_ADDRESS"].first + i + j,
                        line,
                        self.ram,
                    )
                ]
                if not to_all:
                    break
        return writes

    async def handle_filler(
        self, ctx: "BizHawkClientContext", item: ItemData, item_id: int
    ):
        if ItemBase.FREE_MON < item.item_id < ItemBase.FREE_MON + 1000:
            return await self.give_mon(
                ctx, item.item_id - ItemBase.FREE_MON, to_all=False
            )
        return []

    async def handle_rom_startup(self, ctx: "BizHawkClientContext"):
        writes = [
            (data.ram_addresses["POKE_ID_TABLE_ADDRESS"].first + 2, [1], self.ram)
        ]
        for i in range(0, len(ctx.items_received)):
            next_item = ctx.items_received[i]
            item = data.items[items.reverse_offset_item_value(next_item.item)]

            if item.item_id == 1006:
                self.item_info["vatonage"] = True
            if ItemCategory.FIELD_MOVE in item.item_categories:
                writes += await self.handle_give_field_move(ctx, item, next_item.item)

        await bizhawk.write(ctx.bizhawk_ctx, writes)
