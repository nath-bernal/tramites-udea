"""Cálculo de plazos en días hábiles (lunes a viernes).

Simplificación del prototipo: no descuenta festivos colombianos.
"""

from datetime import date, timedelta


def add_business_days(start: date, days: int) -> date:
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def business_days_between(start: date, end: date) -> int:
    """Días hábiles transcurridos después de ``start`` hasta ``end`` inclusive."""
    if end <= start:
        return 0
    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return count
