import json
import os
import time
from datetime import datetime

from .settings import STATE_DIR, inside

EVENTS_DIR = os.path.join(STATE_DIR, "events")


def inside_events(path):
    return inside(EVENTS_DIR, path)


def path_for(day=None):
    return os.path.join(EVENTS_DIR, f"{day or datetime.now():%Y-%m-%d}.jsonl" if day is None else f"{day}.jsonl")


def record(kind, /, **data):
    os.makedirs(EVENTS_DIR, exist_ok=True)
    with open(path_for(), "a") as handle:
        entry = {"at": time.strftime("%H:%M:%S"), "kind": kind}
        entry.update({(key + "_" if key in ("at", "kind") else key): value for key, value in data.items()})
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
