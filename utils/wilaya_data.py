# utils/wilaya_data.py
"""
Loads Algeria's wilaya (province) and baladia/commune (municipality) data
used by the public storefront's shipping form.

Expected source file: data/wilayas.json, with this exact shape
(matching the "Algeria-last-updated-states-69-Wilaia" dataset):

{
  "wilayas": [
    {"wilaya_id": 1, "wilaya_name_latin": "Adrar", "wilaya_name_arabic": "أدرار"},
    ...
  ],
  "communes": [
    {"commune_id": 1, "wilaya_id": 1, "commune_name_latin": "Timekten", "commune_name_arabic": "تيمقتن"},
    ...
  ]
}

TODO: Once Itri provides the real Wilaias.json, drop it at backend/data/wilayas.json
and this loader will pick it up automatically — no code changes needed.
"""

import json
import os
from functools import lru_cache
from typing import List, Dict

DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wilayas.json"
)

# Minimal placeholder so the API doesn't crash before the real file is dropped in.
_PLACEHOLDER_DATA = {
    "wilayas": [
        {"wilaya_id": 1, "wilaya_name_latin": "Adrar", "wilaya_name_arabic": "أدرار"},
        {
            "wilaya_id": 30,
            "wilaya_name_latin": "Ouargla",
            "wilaya_name_arabic": "ورقلة",
        },
        {
            "wilaya_id": 16,
            "wilaya_name_latin": "Alger",
            "wilaya_name_arabic": "الجزائر",
        },
    ],
    "communes": [
        {
            "commune_id": 1,
            "wilaya_id": 1,
            "commune_name_latin": "Timekten",
            "commune_name_arabic": "تيمقتن",
        },
        {
            "commune_id": 2,
            "wilaya_id": 30,
            "commune_name_latin": "Ouargla",
            "commune_name_arabic": "ورقلة",
        },
        {
            "commune_id": 3,
            "wilaya_id": 16,
            "commune_name_latin": "Alger Centre",
            "commune_name_arabic": "الجزائر الوسطى",
        },
    ],
}


@lru_cache(maxsize=1)
def _load_raw_data() -> dict:
    if os.path.exists(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return _PLACEHOLDER_DATA


@lru_cache(maxsize=1)
def get_all_wilayas() -> List[Dict]:
    """Returns list of {wilaya_id, wilaya_name_latin, wilaya_name_arabic}."""
    data = _load_raw_data()
    return sorted(data.get("wilayas", []), key=lambda w: w["wilaya_id"])


@lru_cache(maxsize=128)
def get_communes_by_wilaya(wilaya_id: int) -> List[Dict]:
    """Returns list of {commune_id, wilaya_id, commune_name_latin, commune_name_arabic} for one wilaya."""
    data = _load_raw_data()
    return [c for c in data.get("communes", []) if c["wilaya_id"] == wilaya_id]


def get_wilaya_by_id(wilaya_id: int) -> Dict | None:
    for w in get_all_wilayas():
        if w["wilaya_id"] == wilaya_id:
            return w
    return None


def get_commune_by_id(commune_id: int, wilaya_id: int = None) -> Dict | None:
    data = _load_raw_data()
    for c in data.get("communes", []):
        if c["commune_id"] == commune_id:
            if wilaya_id is not None and c["wilaya_id"] != wilaya_id:
                continue
            return c
    return None
