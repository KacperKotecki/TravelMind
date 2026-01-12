def get_exchange_rate(base_currency: str, target_currency: str = "PLN") -> float | None:
    if base_currency == "EUR" and target_currency == "PLN":
        return 4.3 
    # Tutaj w przyszłości dodasz API NBP
    return None