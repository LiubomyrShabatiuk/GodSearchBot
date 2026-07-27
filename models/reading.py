"""
models/reading.py

Модель літургійного читання.
"""

from dataclasses import dataclass


@dataclass
class Reading:
    """Літургійне читання одного дня."""

    date: str

    title: str
    saint: str

    apostle_name: str
    apostle_ref: str

    gospel_name: str
    gospel_ref: str