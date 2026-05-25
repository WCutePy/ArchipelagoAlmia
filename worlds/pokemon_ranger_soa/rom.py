import struct
from typing import TYPE_CHECKING, Iterable

from BaseClasses import Location
from settings import get_settings
from worlds.Files import APProcedurePatch, APTokenMixin, APTokenTypes
from .data import data, POKE_ID_ROW_ROM_SIZE

if TYPE_CHECKING:
    from . import PokemonRSOA


ARM9_ROM_OFFSET = 0x4000


class PokemonRangerSOAProcedurePatch(APProcedurePatch, APTokenMixin):
    game = "PokemonRangerSOA"
    hash = "f957f5784abf9557be086fdb6fdc74cc"
    patch_file_ending = ".apprsoa"
    result_file_ending = ".nds"

    procedure = [
        ("apply_tokens", ["token_data.bin"]),
    ]

    @classmethod
    def get_source_data(cls) -> bytes:
        with open(get_settings().pokemon_ranger_soa_settings.rom_file, "rb") as infile:
            base_rom_bytes = bytes(infile.read())

        return base_rom_bytes


def write_tokens(
    world: "PokemonRSOA",
    patch: PokemonRangerSOAProcedurePatch,
    starting_se: int = None,
) -> None:

    _nop_instructions(world, patch)

    _remove_field_moves(world, patch)

    patch.write_file("token_data.bin", patch.get_token_binary())


def _nop_instructions(
    world: "PokemonRSOA", patch: PokemonRangerSOAProcedurePatch
) -> None:

    addresses = []

    addresses += data.rom_addresses["INSTRUCTION_STYLER_UPGRADE_SET"].addresses

    if world.options.level_up_type > 0:
        addresses += data.rom_addresses[
            "INSTRUCTION_LEVEL_UP_STYLER_LEVEL_UP"
        ].addresses
        # addresses += data.rom_addresses["INSTRUCTION_LEVEL_UP_MAX_HEALTH_UP"].addresses
        # This sets the game to 0 hp on new save. Causes issues.
    if world.options.rank_up_type > 0:
        addresses += data.rom_addresses["INSTRUCTION_RANGER_RANK_SET"].addresses

    if world.options.styler_model_item > 0:
        addresses += data.rom_addresses["INSTRUCTION_STYLER_MODEL_SET"].addresses

    for address in addresses:
        patch.write_token(
            APTokenTypes.WRITE,
            address,
            struct.pack("<I", 0xE3A00000),
        )


def _remove_field_moves(
    world: "PokemonRSOA", patch: PokemonRangerSOAProcedurePatch
) -> None:
    if world.options.field_move_item == world.options.field_move_item.option_vanilla:
        return

    for pok in data.species.values():

        for val in pok.form_ids:
            address = (
                data.rom_addresses["POKE_ID_TABLE_ADDRESS"].first
                + (val * POKE_ID_ROW_ROM_SIZE)
                + 5
            )
            print(f"{address:x}")
            patch.write_token(
                APTokenTypes.WRITE,
                address,
                (0).to_bytes(1, "little"),
            )
    #
    # for i in range(200):
    #     print("removing shit")
    #     address = data.rom_addresses["POKE_ID_TABLE_ADDRESS"].first + i
    #     patch.write_token(
    #         APTokenTypes.WRITE,
    #         address,
    #         (0).to_bytes(1, "little"),
    #     )

    # patch.write_token(
    #     APTokenTypes.WRITE,
    #     0x2BF1A49,
    #     (0).to_bytes(1, "little"),
    # )


def _path_script_files(world: "PokemonRSOA", patch: PokemonRangerSOAProcedurePatch):
    """For now hardcoded in here, will need changing"""
    addresses = []

    """ school gate"""
    # school gate top, EventRect001104
    # JZ loc_35 -> NOP 0; @31
    # one of potential patches, without breaking story (untested)
    addresses += 0x6A74EC

    # school gate bottom, EventRect001100
    # JZ loc_86 -> NOP 0; @82
    addresses += 0x6A3D48

    """mission 3 forest fire block going back"""
    """an unknown c028Tap05_0 is left in 
    with the vientown jumps"""
    # vientown -> school road, EventRect004101
    # 	JZ loc_35		; @30 -> JMP loc_44
    addresses += (0x06AB200 + 0x78, 0x000D0008)

    # vientown -> beach, EventRect004102
    # JZ loc_43		; @38 -> JMP loc_52
    addresses += (0x6AB400 + 0x98, 0x000D0008)

    # vientown -> chicole path, EventRect004103
    # JZ loc_35		; @30 -> JMP loc_53
    addresses += (0x6AB600 + 0x78, 0x00160008)

    # vien forest -> vientown block during mission 3, EventRect009106
    # JZ loc_36 -> JMP loc_54; @31
    addresses += (0x6BCC00 + 0x7C, 0x00160008)
    # JZ loc_71 -> JZ loc_87; @66
    addresses += (0x6BCC00 + 0x108, 0x00140208)

    for pack in addresses:
        if isinstance(pack, Iterable) and not isinstance(pack, (str, bytes)):
            address, instruction = pack
        else:
            address, instruction = pack, 0x00000000
        patch.write_token(
            APTokenTypes.WRITE,
            address,
            struct.pack("<I", instruction),
        )
