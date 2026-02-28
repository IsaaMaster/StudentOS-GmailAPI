def calculate_seconds(value, unit):
    try:
        val = int(value)
        multipliers = {
            "minutes": 60,
            "hours": 3600,
            "days": 86400
        }
        return val * multipliers.get(unit.lower(), 3600)
    except (ValueError, TypeError):
        return 86400