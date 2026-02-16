import json
from dataclasses import is_dataclass, asdict
from typing import Any
from .data import data, BROWSER_START_ADDRESS, BROWSER_RANK_START_ADDRESS


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
        # Convert to dict safely
        if is_dataclass(obj):
            data = asdict(obj)
        else:
            data = vars(obj)

        new_data = {}

        for key, value in data.items():
            # Skip removed fields
            if key in remove_fields:
                continue

            # Rename if needed
            new_key = rename_fields.get(key, key)
            new_data[new_key] = value

        processed.append(new_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=4)

    print(f"Wrote modified data to {output_file}")


modify_data_to_new_json(
    "worlds/pokemon_ranger_soa/data/items.json",
    data.items,
)
