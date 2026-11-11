"""
SEO Website Checker & Performance Monitor.

Перевіряє доступність сайтів, вимірює час відповіді, дістає <title>
та зберігає результат у CSV-файл. Сайти перевіряються паралельно.

Приклади запуску:
    python seo_checker.py
    python seo_checker.py --file urls.txt --output report.csv --workers 10
"""

import argparse
import csv
import html
import re
import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Список за замовчуванням (використовується, якщо не вказано --file)
DEFAULT_URLS = [
    "https://www.google.com",
    "https://www.python.org",
    "https://github.com",
    "https://example.com/not-found-page",
    "https://this-site-does-not-exist-12345.com",
]

USER_AGENT = "Mozilla/5.0 (compatible; SEO-Audit-Bot/2.0)"
MAX_READ_BYTES = 200_000  # <title> завжди на початку, цілу сторінку читати не треба
FIELDS = ["checked_at", "url", "final_url", "status", "available",
          "response_time_sec", "title", "state"]


def normalize_url(url):
    """Додає https://, якщо схему не вказано."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def load_urls(path):
    """Читає URL з файлу (по одному в рядку, # - коментар)."""
    with open(path, encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    return [line for line in lines if line and not line.startswith("#")]


def extract_title(raw_bytes, charset):
    """Дістає <title> зі сторінки з урахуванням кодування."""
    text = raw_bytes.decode(charset or "utf-8", errors="ignore")
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return "No <title> found"
    # Прибираємо HTML-сутності (&amp;) і зайві пробіли/переноси рядків
    return " ".join(html.unescape(match.group(1)).split()) or "Empty <title>"


def make_result(url, **kwargs):
    """Створює рядок звіту зі значеннями за замовчуванням."""
    result = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "final_url": "N/A",
        "status": "N/A",
        "available": "No",
        "response_time_sec": "N/A",
        "title": "N/A",
        "state": "",
    }
    result.update(kwargs)
    return result


def check_url(url, timeout):
    """Перевіряє один сайт і повертає словник із результатом."""
    start = time.perf_counter()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            code = response.status
            charset = response.headers.get_content_charset()
            body = response.read(MAX_READ_BYTES)
            elapsed = round(time.perf_counter() - start, 3)
            return make_result(
                url,
                final_url=response.geturl(),  # адреса після редиректів
                status=code,
                available="Yes" if code == 200 else "No",
                response_time_sec=elapsed,
                title=extract_title(body, charset),
                state="OK" if code == 200 else "Unexpected status",
            )

    except urllib.error.HTTPError as e:
        # Сервер відповів, але з помилкою (404, 500...)
        elapsed = round(time.perf_counter() - start, 3)
        return make_result(url, status=e.code, response_time_sec=elapsed,
                           state=f"HTTP error: {e.reason}")

    except urllib.error.URLError as e:
        # Таймаут при підключенні теж приходить сюди
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            return make_result(url, state=f"Timeout (>{timeout}s)")
        return make_result(url, state=f"Connection failed: {e.reason}")

    except (socket.timeout, TimeoutError):
        # Таймаут під час читання відповіді
        return make_result(url, state=f"Timeout (>{timeout}s)")

    except Exception as e:  # некоректний URL та інші неочікувані помилки
        return make_result(url, state=f"Error: {e}")


def save_report(results, filename):
    """Зберігає результати у CSV."""
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(description="SEO website checker")
    parser.add_argument("--file", help="файл зі списком URL (по одному в рядку)")
    parser.add_argument("--output", default="seo_performance_report.csv", help="ім'я CSV-файлу")
    parser.add_argument("--timeout", type=float, default=5, help="таймаут, сек (за замовчуванням 5)")
    parser.add_argument("--workers", type=int, default=5, help="кількість паралельних перевірок")
    args = parser.parse_args()

    raw_urls = load_urls(args.file) if args.file else DEFAULT_URLS
    urls = [normalize_url(u) for u in raw_urls]

    print(f"=== Перевіряю {len(urls)} сайтів ===\n")

    # Перевіряємо паралельно; map зберігає початковий порядок URL
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda u: check_url(u, args.timeout), urls))

    for r in results:
        print(f"[{r['status']}] {r['url']} | {r['response_time_sec']}s | {r['state']} | {r['title'][:40]}")

    save_report(results, args.output)

    ok = sum(1 for r in results if r["available"] == "Yes")
    print(f"\nДоступні: {ok}/{len(results)}. Звіт збережено у {args.output}")


if __name__ == "__main__":
    main()
