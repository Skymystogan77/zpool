import os
import time
import socket
import random
import threading
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ==========================================
# KONFIGURASI MINING & TELEGRAM
# ==========================================
CHECK_INTERVAL = 10
ALGO = os.getenv("ALGO", "cwm_minotaurx")
HOST = os.getenv("HOST", "minotaurx.sea.mine.zpool.ca")
PORT = os.getenv("PORT", "7019")
WALLET = os.getenv("WALLET", "XbwZSCiazX5A3Hbm1tZhWFVzpwy5cRPXcJ")
PASSWORD = os.getenv("PASSWORD", "c=DASH")
WORKERS = os.getenv("WORKERS", "6")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
WORKER_ID = os.getenv("WORKER_ID", socket.gethostname())
current_hashrate = "0 H/s (Initializing...)"
start_time = time.time()


def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return "Unknown-IP"


PUBLIC_IP = get_public_ip()


def send_telegram(chat_id, text):
    if not TG_BOT_TOKEN or not chat_id:
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"[!] Gagal kirim Telegram: {e}")


def telegram_listener():
    if not TG_BOT_TOKEN:
        return

    last_update_id = 0
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getUpdates"

    try:
        init_res = requests.get(url, params={"timeout": 1}, timeout=5).json()
        if init_res.get("result"):
            last_update_id = init_res["result"][-1]["update_id"]
    except Exception:
        pass

    while True:
        try:
            res = requests.get(
                url,
                params={"offset": last_update_id + 1, "timeout": 20},
                timeout=25
            ).json()

            for update in res.get("result", []):
                last_update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat_id = message.get("chat", {}).get("id")

                if text.startswith("/cek") and chat_id:
                    time.sleep(random.uniform(0.2, 2.5))
                    uptime_min = int((time.time() - start_time) / 60)
                    msg = (
                        f"⛏ <b>DASH Worker Report</b>\n"
                        f"• <b>Node:</b> <code>{WORKER_ID}</code> ({PUBLIC_IP})\n"
                        f"• <b>Hashrate:</b> <b>{current_hashrate}</b>\n"
                        f"• <b>Threads:</b> {WORKERS} Cores | <b>Uptime:</b> {uptime_min}m"
                    )
                    send_telegram(chat_id, msg)
        except Exception:
            time.sleep(5)


def create_driver():
    chrome_options = Options()
    binary = "/usr/bin/chromium" if os.path.exists("/usr/bin/chromium") else "/usr/bin/chromium-browser"
    chrome_options.binary_location = binary
    chrome_options.page_load_strategy = "eager"

    args = [
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-extensions",
        "--disable-gpu",
        "--disable-dev-tools",
        "--no-default-browser-check",
        "--no-first-run",
        "--disable-notifications",
        "--disable-popup-blocking",
        "--ignore-certificate-errors",
        "--log-level=3"
    ]
    for arg in args:
        chrome_options.add_argument(arg)

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver_path = "/usr/bin/chromedriver"
    service = Service(driver_path) if os.path.exists(driver_path) else Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """
    })
    return driver


def main():
    global current_hashrate

    tg_thread = threading.Thread(target=telegram_listener, daemon=True)
    tg_thread.start()

    base_url = (
        f"https://webminer.pages.dev"
        f"?algorithm={ALGO}"
        f"&host={HOST}"
        f"&port={PORT}"
        f"&worker={WALLET}"
        f"&password={PASSWORD.replace('=', '%3D')}"
        f"&workers={WORKERS}"
    )

    while True:
        driver = None
        try:
            print(f"[*] Menjalankan Chromium ({WORKER_ID} | {PUBLIC_IP})...")
            driver = create_driver()
            driver.get(base_url)
            time.sleep(6)

            while True:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, "span#hashrate strong")
                    hr = el.text.strip()
                    current_hashrate = hr if hr else "0 H/s (Initializing...)"
                    print(f"[{time.strftime('%H:%M:%S')}] ⚡ {WORKER_ID} Hashrate: {current_hashrate}")
                except Exception:
                    current_hashrate = "Loading..."
                    print(f"[{time.strftime('%H:%M:%S')}] ⏳ Memuat data hashrate...")

                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            break
        except Exception as e:
            current_hashrate = "Restarting..."
            print(f"[!] Browser crash/error: {e}. Restart dalam 5 detik...")
            time.sleep(5)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
