import logging
import os
import pathlib
import struct
import sys
from types import ModuleType
from typing import TYPE_CHECKING, Iterable, Dict, Any, Callable, Protocol
from zipfile import ZipFile, ZIP_DEFLATED

from orjson import orjson

import NetUtils
import Utils
from BaseClasses import Location
from settings import get_settings
from worlds.Files import (
    APProcedurePatch,
    APTokenMixin,
    APTokenTypes,
    APAutoPatchInterface,
)
from .data import data, POKE_ID_ROW_ROM_SIZE
from .options import RandomizePokemon

if TYPE_CHECKING:
    from . import PokemonRSOA


ARM9_ROM_OFFSET = 0x4000


class PokemonRSOAPatch(APAutoPatchInterface):
    game = "PokemonRangerSOA"
    patch_file_ending = ".apprsoa"
    result_file_ending = ".nds"

    def __init__(self, path: str, player=None, player_name="", world=None):
        self.world: "PokemonRSOA" = world
        self.files: dict[str, bytes] = {}
        super().__init__(path, player, player_name, "")

    def write_contents(self, opened_zipfile: ZipFile) -> None:
        super().write_contents(opened_zipfile)
        PatchMethods.write_contents(self, opened_zipfile)

    def get_manifest(self) -> Dict[str, Any]:
        return PatchMethods.get_manifest(self, super().get_manifest())

    def patch(self, target: str) -> None:
        PatchMethods.patch(self, target, "prsoa")

    def read_contents(self, opened_zipfile: ZipFile) -> Dict[str, Any]:
        return PatchMethods.read_contents(
            self, opened_zipfile, super().read_contents(opened_zipfile)
        )

    def get_file(self, file: str) -> bytes:
        return PatchMethods.get_file(self, file)


class PatchMethods:

    @staticmethod
    def write_contents(patch: PokemonRSOAPatch, opened_zipfile: ZipFile) -> None:
        from .patch import map_patch, species_patch

        procedures: list[str] = ["base_patch", "quest_patch"]

        if patch.world.options.randomize_pokemon != RandomizePokemon.option_vanilla:
            procedures.append("map_patch")
            map_patch.write_patch(patch, opened_zipfile)

        if patch.world.options.randomize_partners != RandomizePokemon.option_vanilla:
            procedures.append("species_patch")
            species_patch.write_patch(patch, opened_zipfile)

        opened_zipfile.writestr("procedures.txt", "\n".join(procedures))
        opened_zipfile.writestr(
            "slot_data.json",
            orjson.dumps(NetUtils.convert_to_base_types(patch.world.fill_slot_data())),
        )  # for when I need the slot data

    @staticmethod
    def get_manifest(
        patch: PokemonRSOAPatch, manifest: dict[str, Any]
    ) -> Dict[str, Any]:
        manifest["prsoa_patch_format"] = 10
        return manifest

    @staticmethod
    def patch(patch: PokemonRSOAPatch, target: str, version_name: str) -> None:
        patch.read()

        # if pathlib.Path(target).exists():
        #     with open(target, "rb") as f:
        #         header_part = f.read(0xA0)
        #         found_rom_version = tuple(header_part[0x9D:0xA0])
        #         if version.rom() == found_rom_version:
        #             return

        logging.warning(f"Starting rom patching")

        from .apnds import rom as apnds_rom
        from .patch import base_patch, map_patch, quest_patch, species_patch

        patch_procedures: dict[
            str,
            Callable[
                [
                    apnds_rom.Rom,
                    str,
                    PokemonRSOAPatch,
                    dict[str, bytes | bytearray],
                ],
                None,
            ],
        ] = {
            "base_patch": base_patch.patch,
            "map_patch": map_patch.patch,
            "quest_patch": quest_patch.patch,
            "species_patch": species_patch.patch,
        }

        files_dump: dict[str, bytes | bytearray] = {}
        base_data = get_base_rom_bytes(version_name)
        rom = apnds_rom.Rom.from_bytes(base_data)
        procedures: list[str] = str(
            patch.get_file("procedures.txt"), "utf-8"
        ).splitlines()
        for prod in procedures:
            patch_procedures[prod](rom, __name__, patch, files_dump)

        class PRSOAPatchPlugin(Protocol):
            name: str
            patch: Callable[
                [
                    apnds_rom.Rom,
                    PokemonRSOAPatch,
                    dict[str, bytes | bytearray],
                    list[ModuleType],
                ],
                None,
            ]

        plugins = []
        plugin_errors = []
        for module_name, module_type in sys.modules.items():
            if module_name.startswith("worlds.pokemon_ranger_soa_"):
                plugins.append((module_name, module_type))
        for module_name, module_type in plugins:
            try:
                if not hasattr(module_type, "Plugin"):
                    logging.warning(
                        f"{module_name[7:]} has the patch plugin naming scheme, "
                        f"but doesn't contain a class named 'Plugin' in __init__.py"
                    )
                    continue
                if not isinstance(module_type.Plugin, type):
                    raise Exception(f"{module_name[7:]}.Plugin is not a class")
                plugin: PRSOAPatchPlugin = getattr(module_type, "Plugin")
                if not hasattr(plugin, "patch") or not isinstance(
                    plugin.patch, Callable
                ):
                    raise Exception(
                        f"{module_name[7:]}.Plugin doesn't have a method called 'patch'"
                    )
                logging.warning(f"Doing this plugin: {module_name}, {module_type}")
                plugin.patch(rom, patch, files_dump, plugins)
            except Exception as e:
                for arg in e.args:
                    plugin_errors.append(f"[{module_name[7:]}] {arg}")
        if plugin_errors:
            import ctypes

            message = f"Following error{'s' if len(plugin_errors) > 1 else ''} appeared during patch plugin loading:\n"
            message += "".join(("\n" + error) for error in plugin_errors)
            message += (
                "\n\nThe affected plugins might have only partially been applied.\n"
                "Click OK to continue or CANCEL to abort patching."
            )
            if ctypes.windll.user32.MessageBoxW(0, message, "Warning", 1) == 2:
                raise Exception(
                    "Patching was aborted by the user after a plugin threw an error"
                )
            logging.warning(message)

        with open(target, "wb") as f:
            f.write(rom.to_bytes())
        # if get_settings()["pokemon_ranger_soa_settings"].get(
        #     "dump_patched_files", None
        # ):
        #     with ZipFile(
        #         target.replace(".nds", "_files_dump.zip"), "w", ZIP_DEFLATED, True, 9
        #     ) as dump:
        #         for path, data in files_dump.items():
        #             dump.writestr(path, data)

    @staticmethod
    def read_contents(
        patch: PokemonRSOAPatch, opened_zipfile: ZipFile, manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        for file in opened_zipfile.namelist():
            if file not in ["archipelago.json"]:
                patch.files[file] = opened_zipfile.read(file)

        # found_version: tuple[int, ...] = tuple(manifest["prsoa_patch_format"])
        # accept = version.patch_accept(found_version)
        #
        # if accept == 1:
        #     raise Exception(f"File (patch version: {version_str(manifest['prsoa_patch_format'])}) too new "
        #                     f"for this apworld (patch version: {version_str(version.patch_file())}). "
        #                     f"Please update your apworld.")
        # elif accept == -1:
        #     raise Exception(f"File (patch version: {version_str(manifest['prsoa_patch_format'])}) too old "
        #                     f"for this apworld (patch version: {version_str(version.patch_file())}). "
        #                     f"Either re-generate your world or downgrade to an older apworld version.")

        return manifest

    @staticmethod
    def get_file(patch: PokemonRSOAPatch, file: str) -> bytes:
        if file not in patch.files:
            patch.read()
        return patch.files[file]


def get_base_rom_bytes(version: str, file_name: str = "") -> bytes:
    while True:
        if not file_name:
            file_name = get_base_rom_path(version, file_name)
        with open(file_name, "rb") as file:
            base_rom_bytes = bytes(file.read())
        header_bytes = base_rom_bytes[:18]
        # TODO verify proper rom
        return base_rom_bytes


def get_base_rom_path(version: str, file_name: str = "") -> str:
    if not file_name:
        file_name = get_settings()["pokemon_ranger_soa_settings"]["rom_file"]
    if not os.path.exists(file_name):
        file_name = Utils.user_path(file_name)
    return file_name


class PokemonRangerSOAProcedurePatch(APProcedurePatch, APTokenMixin):
    game = "PokemonRangerSOA"
    hash = "f957f5784abf9557be086fdb6fdc74cc"
    patch_file_ending = ".apprsoa_old"
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
