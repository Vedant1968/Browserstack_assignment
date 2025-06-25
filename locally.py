import os
import time
import re
from collections import Counter
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from urllib.parse import urljoin

# Load .env
load_dotenv()
API_KEY = os.getenv("RAPIDAPI_KEY")

# Translation via RapidAPI
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

# Repeated words function
def extract_repeated_words(texts, min_count=3):
    text = ' '.join(texts).lower()
    words = re.findall(r'\b\w+\b', text)
    freq = Counter(words)
    return {word: count for word, count in freq.items() if count >= min_count}

# Setup Chrome WebDriver
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

try:
    driver.get("https://elpais.com/")

    # Accept cookies
    try:
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
        )
        accept_btn.click()
        print("✅ Accepted cookies.")
    except:
        print("✅ No cookie popup.")

    # Navigate to Opinión section
    opinion = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Opinión"))
    )
    opinion.click()

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article")))
    time.sleep(2)

    articles = driver.find_elements(By.CSS_SELECTOR, "article")[:5]

    print("\n==== 📰 ORIGINAL ARTICLES (Spanish) ====\n")
    titles = []
    contents = []

    for idx, article in enumerate(articles):
        try:
            title = article.find_element(By.TAG_NAME, "h2").text.strip()
            content = article.find_element(By.TAG_NAME, "p").text.strip()
            print(f"🧾 TITLE: {title}\n📄 CONTENT: {content}\n")

            titles.append(title)
            contents.append(content)

            # Download image if available
            try:
                img = article.find_element(By.CSS_SELECTOR, "img")
                img_url = img.get_attribute("src")
                img_url = urljoin(driver.current_url, img_url)

                img_data = requests.get(img_url).content
                safe_title = re.sub(r'[^\w\-_\. ]', '_', title[:50])
                filename = f"images/{safe_title}.jpg"

                with open(filename, "wb") as f:
                    f.write(img_data)
                print(f"✅ Saved image: {filename}")
            except Exception as img_err:
                print(f"❗ No image found for article {idx+1} - {img_err}")

        except Exception as e:
            print(f"❗ Skipping article due to error: {e}")
            continue

    print("\n==== 🌐 TRANSLATED TITLES (English) ====\n")
    translated = translate_texts(titles)
    for i, t in enumerate(translated):
        print(f"🔹 {t}")

    print("\n==== 🔁 REPEATED WORDS (>2 times) ====\n")
    repeated = extract_repeated_words(contents)
    for word, count in repeated.items():
        print(f"{word}: {count}")

finally:
    driver.quit()
