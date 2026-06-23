from settings import get_settings
from worlds.Files import APProcedurePatch, APTokenMixin


class PokemonLinkProcedurePatch(APProcedurePatch, APTokenMixin):
    game = "Pokemon Trozei"
    hash = "5af68afc469ee54adc3721d9d8913904"
    patch_file_ending = ".applink"
    result_file_ending = ".nds"

    procedure = [
    ]

    @classmethod
    def get_source_data(cls) -> bytes:
        with open(get_settings().pokemon_trozei_settings.link_rom_file, "rb") as infile:
            base_rom_bytes = bytes(infile.read())

        return base_rom_bytes