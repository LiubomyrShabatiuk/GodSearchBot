"""
scan_ugcc.py

Завантажує сторінку календаря УГКЦ
та зберігає її локально для аналізу.

GodSearchBot v2.0
"""

from pathlib import Path
import requests

URL = "https://ugcc.ua"

OUTPUT_DIR = Path("data/debug")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():

    print("=" * 50)
    print(" GodSearchBot Calendar Scanner")
    print("=" * 50)

    print(f"\nОтримання сторінки:\n{URL}")

    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "GodSearchBot/2.0"
        }
    )

    print(f"HTTP статус: {response.status_code}")

    html_file = OUTPUT_DIR / "ugcc_home.html"

    html_file.write_text(
        response.text,
        encoding="utf-8"
    )

    print(f"\nHTML збережено:\n{html_file}")

    print("\nПерші 500 символів:\n")
    print(response.text[:500])

    print("\nГотово.")


if __name__ == "__main__":
    main()