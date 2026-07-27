"""
importers/base_importer.py

Базовий клас для всіх імпортерів календаря.

GodSearchBot v2.1
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from models.reading import Reading


class BaseImporter(ABC):
    """
    Базовий клас для імпортерів.

    Усі імпортери (PDF, HTML тощо) повинні
    реалізувати метод import_calendar().
    """

    def __init__(self, source: str | Path):

        self.source = Path(source)

    @abstractmethod
    def import_calendar(self) -> Iterable[Reading]:
        """
        Повертає список Reading.
        """
        raise NotImplementedError

    def exists(self) -> bool:
        """
        Перевіряє існування файлу.
        """
        return self.source.exists()

    def validate(self) -> None:
        """
        Перевіряє, що файл існує.
        """

        if not self.exists():
            raise FileNotFoundError(
                f"Файл не знайдено: {self.source}"
            )

    def __str__(self):

        return f"{self.__class__.__name__}({self.source})"