import json
from dataclasses import is_dataclass, asdict
from typing import Any
from .data import data, SpeciesData


def modify_data_to_new_json(
    output_file: str,
    instance: list[Any],
    remove_fields: set[str] | None = None,
    rename_fields: dict[str, str] | None = None,
):
    remove_fields = remove_fields or set()
    rename_fields = rename_fields or {}

    processed = []

    for obj in instance:
        if is_dataclass(obj):
            data = asdict(obj)

        elif isinstance(obj, dict):
            data = obj

        elif isinstance(obj, (list, tuple)):
            processed.append(list(obj))
            continue

        elif isinstance(obj, (str, int, float, bool)):
            processed.append(obj)
            continue

        elif hasattr(obj, "__dict__"):
            data = vars(obj)

        else:
            processed.append(str(obj))
            continue

        new_data = {}

        for key, value in data.items():
            if key in remove_fields:
                continue
            new_key = rename_fields.get(key, key)
            new_data[new_key] = value

        processed.append(new_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=4)


import pkgutil
import csv
import io
from typing import List, Dict, Any


def load_csv_data(data_name: str) -> List[Dict[str, Any]]:
    raw_data = pkgutil.get_data(__name__, "data/" + data_name)

    if raw_data is None:
        raise FileNotFoundError(f"Could not find data/{data_name}")

    text = raw_data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    return list(reader)


def add_national_desk():
    pok = list(data.species.values())

    modify_data_to_new_json(
        "worlds/pokemon_ranger_soa/data/new_species.json",
        pok,
        {
            "poke_id_indexes",
        },
    )


# add_national_desk()
modify_data_to_new_json(
    "worlds/pokemon_ranger_soa/data/new_species.json",
    data.species.values(),
    {"poke_id_indexes"},
)
