"""
Перевірка доступності вебсайтів.

Скрипт бере список URL, робить HTTP-запит до кожного
і зберігає результат у файл report.csv.
"""

import csv
import urllib.error
import urllib.request

# Список сайтів для перевірки (можна змінити на свій)
URLS = [
    "https://www.google.com",
    "https://www.python.org",
    "https://github.com",
    "https://example.com/not-found-page",
    "https://this-site-does-not-exist-12345.com",
]

TIMEOUT = 5  # скільки секунд чекати відповідь від сайту


def check_url(url):
    """Перевіряє один сайт. Повертає (статус, повідомлення)."""
    try:
        # Додаємо User-Agent, бо деякі сайти блокують запити без нього
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            code = response.status
            message = "OK" if code == 200 else "Неочікуваний статус"
            return code, message

    except urllib.error.HTTPError as e:
        # Сайт відповів, але з помилкою (404, 500 тощо)
        return e.code, f"HTTP помилка: {e.reason}"

    except urllib.error.URLError as e:
        # Сайт недоступний (немає DNS, відмовлено у з'єднанні тощо)
        return None, f"Не вдалося підключитись: {e.reason}"

    except TimeoutError:
        # Сайт не відповів вчасно
        return None, "Час очікування вичерпано"

    except Exception as e:
        # Будь-яка інша несподівана помилка (наприклад, невірний URL)
        return None, f"Помилка: {e}"


def main():
    results = []

    for url in URLS:
        status, message = check_url(url)
        available = status == 200  # доступний лише якщо код 200
        results.append([url, status if status else "-", "Так" if available else "Ні", message])
        print(f"{url} -> {status} ({message})")

    # Зберігаємо результати у CSV-файл
    with open("report.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "Status code", "Доступний", "Повідомлення"])
        writer.writerows(results)

    print("\nЗвіт збережено у report.csv")


if __name__ == "__main__":
    main()
