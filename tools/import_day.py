"""
tools/import_day.py

Імпорт одного дня з Časoslov у SQLite.
"""

from importers.casoslov_importer import CasoslovImporter
from services.readings_database import (
    readings_db,
    APOSTLE,
    GOSPEL,
)


def import_day(date: str):

    print(f"\nІмпортуємо {date}...\n")

    importer = CasoslovImporter()

    reading = importer.get_day(date)

    # очищаємо попередній імпорт цього дня
    conn = readings_db.connect()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM readings WHERE date=?",
        (date,)
    )

    conn.commit()
    conn.close()

    # Апостол
    if reading.apostle_ref:

        readings_db.save(
            date=date,
            reading_type=APOSTLE,
            reference=reading.apostle_ref,
            position=1
        )

    # Євангеліє
    if reading.gospel_ref:

        readings_db.save(
            date=date,
            reading_type=GOSPEL,
            reference=reading.gospel_ref,
            position=1
        )

    # Перевіряємо результат
    rows = readings_db.get(date)

    print("==============================================")

    print("Дата:")
    print(date)

    print()

    print("Знайдено читань:", len(rows))

    print()

    for row in rows:

        if row["reading_type"] == APOSTLE:
            name = "Апостол"
        elif row["reading_type"] == GOSPEL:
            name = "Євангеліє"
        else:
            name = "Невідомо"

        print(
            f"{name} #{row['position']}: "
            f"{row['reference']}"
        )

    print()

    print("==============================================")


if __name__ == "__main__":

    import_day("2026-07-14")