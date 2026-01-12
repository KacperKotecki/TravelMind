# 1. Używamy lekkiego obrazu Pythona (wersja slim jest mniejsza i bezpieczniejsza)
FROM python:3.12-slim

# 2. Ustawiamy katalog roboczy wewnątrz kontenera
WORKDIR /app

# 3. Kopiujemy plik zależności i instalujemy je
# Robimy to PRZED kopiowaniem kodu, żeby Docker wykorzystał Cache (szybsze buildy)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Kopiujemy resztę kodu aplikacji
COPY . .

# 5. Ustawiamy zmienne środowiskowe dla bezpieczeństwa
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 6. Otwieramy port (domyślny dla Gunicorna/Flaska to często 8000 lub 5000)
EXPOSE 8000

# 7. Komenda startowa - Używamy GUNICORN zamiast flask run
# -w 4: cztery worker processy (zależnie od rdzeni CPU na VPS)
# -b 0.0.0.0:8000: nasłuchuj na wszystkich interfejsach na porcie 8000
# run:app : plik run.py, obiekt app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "run:app"]