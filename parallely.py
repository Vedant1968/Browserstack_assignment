import os
import time
import re
import threading
from collections import Counter
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from urllib.parse import urljoin

load_dotenv()
API_KEY = os.getenv("RAPIDAPI_KEY")
BROWSERSTACK_USERNAME = os.getenv("BROWSERSTACK_USERNAME")
BROWSERSTACK_ACCESS_KEY = os.getenv("BROWSERSTACK_ACCESS_KEY")

BROWSERSTACK_URL = "https://hub.browserstack.com/wd/hub"

platforms = {
    "Chrome_Win11": {
        "browserName": "Chrome",
        "os": "Windows",
        "osVersion": "11"
    },
    "Edge_Win10": {
        "browserName": "Edge",
        "os": "Windows",
        "osVersion": "10"
    },
    "Safari_Mac": {
        "browserName": "Safari",
        "os": "OS X",
        "osVersion": "Ventura"
    },
    "Chrome_Android": {
        "deviceName": "Samsung Galaxy S22",
        "realMobile": "true",
        "osVersion": "12.0"
    },
    "Firefox_Ubuntu": {
        "browserName": "Firefox",
        "os": "OS X",
        "osVersion": "Monterey"
    }
}

def translate_texts(texts):
    url = "https://rapid-translate-multi-traduction.p.rapidapi.com/t"
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "rapid-translate-multi-traduction.p.rapidapi.com"
    }
    payload = {
        "from": "es",
        "to": "en",
        "e": "",
        "q": texts if isinstance(texts, list) else [texts]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

def extract_repeated_words(texts, min_count=3):
    text = ' '.join(texts).lower()
    words = re.findall(r'\b\w+\b', text)
    freq = Counter(words)
    return {word: count for word, count in freq.items() if count >= min_count}

def run_test(name, config):
    print(f"\n\U0001F680 Starting thread: {name}")

    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.safari.options import Options as SafariOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions

    browser = config.get("browserName", "")
    if browser == "Chrome":
        options = ChromeOptions()
    elif browser == "Edge":
        options = EdgeOptions()
    elif browser == "Safari":
        options = SafariOptions()
    elif browser == "Firefox":
        options = FirefoxOptions()
    else:
        options = ChromeOptions()

    options.set_capability("browserName", browser)
    options.set_capability("bstack:options", {
        "os": config.get("os", ""),
        "osVersion": config.get("osVersion", ""),
        "deviceName": config.get("deviceName", ""),
        "realMobile": config.get("realMobile", "false"),
        "projectName": "El Pais Scraper",
        "buildName": "Parallel Run",
        "sessionName": name,
        "userName": BROWSERSTACK_USERNAME,
        "accessKey": BROWSERSTACK_ACCESS_KEY
    })

    try:
        driver = webdriver.Remote(
            command_executor=BROWSERSTACK_URL,
            options=options
        )

        driver.get("https://elpais.com/")
        time.sleep(2)

        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            ).click()
            print("✅ Accepted cookies.")
        except:
            print("✅ No cookie popup.")

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Opinión"))
        ).click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article")))
        time.sleep(2)
        articles = driver.find_elements(By.CSS_SELECTOR, "article")[:5]

        print(f"\n==== 📰 ORIGINAL ARTICLES ({name}) ====")
        titles, contents = [], []

        for idx, article in enumerate(articles):
            try:
                title = article.find_element(By.TAG_NAME, "h2").text.strip()
                content = article.find_element(By.TAG_NAME, "p").text.strip()
                print(f"\n📞 TITLE: {title}\n📄 CONTENT: {content}")
                titles.append(title)
                contents.append(content)
            except Exception as e:
                print(f"❗ Skipping article due to error extracting text: {e}")
                continue

            try:
                img = article.find_element(By.CSS_SELECTOR, "img")
                img_url = urljoin(driver.current_url, img.get_attribute("src"))
                img_data = requests.get(img_url).content
                safe_title = re.sub(r'[^\w\-\_\. ]', '_', title[:50])
                filename = f"images/{name}_{safe_title}.jpg"
                os.makedirs("images", exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(img_data)
                print(f"✅ Saved image: {filename}")
            except Exception as img_err:
                print(f"❗ No image found - Reason: {type(img_err).__name__}")

        if titles:
            print(f"\n==== ✨ TRANSLATED TITLES ({name}) ====")
            for t in translate_texts(titles):
                print(f"🔹 {t}")

        if contents:
            print(f"\n==== ♻ REPEATED WORDS ({name}) ====")
            for word, count in extract_repeated_words(contents).items():
                print(f"{word}: {count}")

    except Exception as e:
        print(f"❌ Error in {name}: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

threads = [
    threading.Thread(target=run_test, args=(name, config))
    for name, config in platforms.items()
]

for t in threads:
    t.start()
for t in threads:
    t.join()

print("\n✅ All tests completed.")
