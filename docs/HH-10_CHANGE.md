# HH-10 — brak pomiaru sensora bez sztucznego zera

## Problem i odtworzenie

Brakujące pola MQTT były odczytywane przez `get(..., 0.0)`, więc brak
temperatury lub wilgotności wyglądał jak prawdziwy pomiar `0`. Ten sam zamiennik
trafiał do `SensorService.record_reading` i mógł zostać zapisany w PostgreSQL.

## Zmiana

- Adapter sensora zwraca `None` dla pola nieobecnego, `null`, nieliczbowego lub
  nieskończonego. Wartość `0` pozostaje poprawnym pomiarem.
- Persystencja wymaga obu pól temperatury i wilgotności oraz odrzuca tylko brak,
  wartości nieliczbowe i NaN/inf. Nie powstaje wpis z podstawionym zerem.
- Sygnały Qt używają typu `object`, aby przekazać `None` do warstwy QML.
  Dodano `Ui.sensor(value, unit)`, które renderuje `brak danych`; istniejący
  ekran nie ma jeszcze osobnej karty sensorów podłączonej do tych sygnałów,
  więc jej wizualne użycie pozostaje do rozszerzenia UI.
- Callback kompozycji także nie wykonuje `float(None)` i publikuje `None`.

## Testy

`Tests/Unit/test_sensor_missing_data.py` sprawdza brakujące pola, `null`, błędne
wartości, prawdziwe zera oraz zapis do fake repozytorium. Wykonano razem z
testami persystencji MQTT:

    ../HomeHub-phase3/.venv/bin/python Tests/run_offline.py --pytest-only Tests/Unit/test_sensor_missing_data.py Tests/Unit/test_sensor_persistence.py

Wynik: **12 passed**. Nie użyto połączenia MQTT, bazy danych ani sprzętu.
Pełny runner/QML należy uruchomić przed PR; testy QML nie mają obecnie osobnej
karty sensorów do kliknięcia.

## Ryzyko i rollback

Kod kliencki, który traktował `0` jako brak danych, musi teraz obsługiwać `None`;
to jest zamierzona zmiana semantyki. Zmieniono typ sygnału Qt, lecz nie zmieniono
istniejących wartości klimatyzacji ani pogody. Wycofanie wymaga revertu commita
w osobnym PR; brak migracji danych i zmian produkcyjnej konfiguracji.
