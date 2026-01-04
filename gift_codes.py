import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from datetime import datetime
import os
import csv

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

PLAYER_IDS_FILE = config.get("PLAYER_IDS_FILE")
URL = config.get("URL")
GIFT_CODE = config.get("GIFT_CODE")
WAIT = config.get("WAIT")
MAX_THREADS = config.get("MAX_THREADS")
MAX_RETRIES = config.get("MAX_RETRIES")
RESULTS_DIR = config.get("RESULTS_DIR")

os.makedirs(RESULTS_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
RESULTS_FILE = os.path.join(RESULTS_DIR, f"{timestamp}_{GIFT_CODE}.csv")

with open(PLAYER_IDS_FILE, "r") as f:
    PLAYER_IDS = [line.strip() for line in f if line.strip()]

print(f"Loaded Player IDs: {PLAYER_IDS}\n")

redeemed_count = 0
claimed_count = 0
error_ids = []

file_lock = threading.Lock()

with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["player_id", "attempt", "status", "message"])


def save_result(player_id, attempt, status, message):
    with file_lock:
        with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([player_id, attempt, status, message])


def process_player(player_id):
    global redeemed_count, claimed_count, error_ids

    for attempt in range(1, MAX_RETRIES + 2):
        driver = webdriver.Chrome()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

        wait = WebDriverWait(driver, 10)

        try:
            driver.get(URL)

            gift_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Gift Code']")))
            gift_input.clear()
            gift_input.send_keys(GIFT_CODE.upper())
            time.sleep(WAIT)

            player_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Player ID']")))
            player_input.clear()
            player_input.send_keys(player_id)
            time.sleep(WAIT)

            login_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'login_btn') and not(contains(@class,'disabled'))]")))
            login_btn.click()
            time.sleep(WAIT)

            confirm_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'exchange_btn') and not(contains(@class,'disabled'))]")))
            confirm_btn.click()
            time.sleep(WAIT)

            popup_text_elem = wait.until(EC.presence_of_element_located((By.XPATH, "//p[@class='msg']")))
            popup_text = popup_text_elem.text

            if "Redeemed, please claim the rewards in your mail!" in popup_text:
                print(f"✅ Player ID: {player_id} -> \"{popup_text}\", attempt: {attempt}")
                with file_lock:
                    redeemed_count += 1
                save_result(player_id, attempt, "REDEEMED", popup_text)
                return

            elif "Already claimed, unable to claim again." in popup_text:
                print(f"✅ Player ID: {player_id} -> \"{popup_text}\", attempt: {attempt}")
                with file_lock:
                    claimed_count += 1
                save_result(player_id, attempt, "ALREADY_CLAIMED", popup_text)
                return

            else:
                raise Exception(popup_text)

        except Exception as e:
            print(f"❌ Failed for Player ID {player_id}: \"{e}\", attempt: {attempt} ❌")
            save_result(player_id, attempt, "ERROR", str(e))

            if attempt == MAX_RETRIES + 1:
                with file_lock:
                    error_ids.append(player_id)
                save_result(player_id, "ERROR", str(e))

            time.sleep(WAIT)

        finally:
            driver.quit()


with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(process_player, pid) for pid in PLAYER_IDS]
    for _ in as_completed(futures):
        pass


total_players = len(PLAYER_IDS)
successful = redeemed_count + claimed_count
failed = len(error_ids)

print("\n------------------------------------ Statistics ------------------------------------\n")
print(f"Total players: {total_players}\n")

print(f"Successfully processed: {successful}\n")
print(f"  Redeemed: {redeemed_count}")
print(f"  Already claimed: {claimed_count}\n")

print(f"Failed: {failed}")
if error_ids:
    print("Player IDs with errors:", ", ".join(error_ids))

print(f"\nResults saved to: {RESULTS_FILE}")
