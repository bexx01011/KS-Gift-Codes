import json
import threading
import csv
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from helper import *

with open("config.json", "r") as f:
    config = json.load(f)

os.makedirs(config["RESULTS_DIR"], exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
RESULTS_FILE = os.path.join(config["RESULTS_DIR"], f"{timestamp}_{config['GIFT_CODE']}.csv")

PLAYER_IDS, sheet_counts = load_player_ids_from_xlsx(config["PLAYER_IDS_FILE"])

print("Loaded players:")
print(f"  • RAW: {sheet_counts['RAW']}")
print(f"  • Others: {sheet_counts['Others']}\n")

print("\n------------------------------------ Logs ------------------------------------\n", flush=True)

file_lock = threading.Lock()

counters = {
    "redeemed": 0,
    "claimed": 0,
    "errors": []
}

if config["SAVE_RESULTS"]:
    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["player_id", "attempt", "status", "message"])

chunk_size = len(PLAYER_IDS) // config["MAX_THREADS"] + 1
chunks = list(chunk_list(PLAYER_IDS, chunk_size))

with ThreadPoolExecutor(max_workers=config["MAX_THREADS"]) as executor:
    futures = [
        executor.submit(
            worker,
            chunk,
            config,
            RESULTS_FILE,
            file_lock,
            counters
        )
        for chunk in chunks
    ]

    for _ in as_completed(futures):
        pass

print("\n------------------------------------ Statistics ------------------------------------\n", flush=True)
print(f"Total players: {len(PLAYER_IDS)}", flush=True)
print(f"Successfully processed: {counters['redeemed'] + counters['claimed']}", flush=True)
print(f"  Redeemed: {counters['redeemed']}", flush=True)
print(f"  Already claimed: {counters['claimed']}", flush=True)
print(f"Failed: {len(counters['errors'])}", flush=True)

if counters["errors"]:
    print("Player IDs with errors:", ", ".join(counters["errors"]), flush=True)

