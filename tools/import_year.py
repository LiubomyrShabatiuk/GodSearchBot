"""
GodSearchBot

Імпорт усіх літургійних читань за 2026 рік.

Запуск:

python -m tools.import_year
"""

from datetime import date, timedelta
import traceback

from importers.casoslov_importer import CasoslovImporter
from services.readings_database import ReadingsDatabase


START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)


def daterange(start: date, end: date):
    current = start

    while current <= end:
        yield current
        current += timedelta(days=1)


def main():

    importer = CasoslovImporter()
    readings_db = ReadingsDatabase()

    total_days = 0
    total_readings = 0
    errors = 0

    total_count = (END_DATE - START_DATE).days + 1

    print()
    print("=" * 60)
    print("IMPORTING YEAR 2026")
    print("=" * 60)
    print()

    for index, current_date in enumerate(
        daterange(START_DATE, END_DATE),
        start=1
    ):

        day = current_date.isoformat()

        print(f"[{index:03}/{total_count}] {day}", end=" ")

        try:

            reading = importer.get_day(day)

            readings_db.delete_date(day)

            saved = 0

            #
            # Apostle
            #

            if reading.apostle_ref:

                readings_db.save(
                    date=day,
                    reading_type=1,
                    reference=reading.apostle_ref,
                    position=1
                )

                saved += 1

            #
            # Gospel
            #

            if reading.gospel_ref:

                readings_db.save(
                    date=day,
                    reading_type=2,
                    reference=reading.gospel_ref,
                    position=1
                )

                saved += 1

            total_days += 1
            total_readings += saved

            print(f"✔ (+{saved})")

        except Exception as e:

            errors += 1

            print("✖")
            print(f"    ERROR: {e}")

            traceback.print_exc()

            continue

    print()
    print("=" * 60)
    print("IMPORT FINISHED")
    print("=" * 60)
    print(f"Days processed : {total_days}")
    print(f"Readings saved : {total_readings}")
    print(f"Errors         : {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()