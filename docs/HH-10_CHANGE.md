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
- Sygnały Qt używają `QVariant`, aby przekazać liczby i `None` do QML.
  Pierwsza implementacja `object` powodowała `Cannot assign PySide::PyObjectWrapper
  to double`; regresję odtworzono na prawdziwym QML i poprawiono.
- Istniejąca `TemperatureMap.qml` odbiera te sygnały. Używa teraz `Ui.sensor`,
  pokazuje `brak danych` dla brakującego pomiaru, zachowuje neutralny kolor
  pokoju i ponownie rysuje mapę po zmianie wilgotności. Poprzednia informacja
  o braku widoku sensorów była błędna; nie dodano nowego układu interfejsu.
- Callback kompozycji także nie wykonuje `float(None)` i publikuje `None`.

## Testy

`Tests/Unit/test_sensor_missing_data.py` sprawdza brakujące pola, `null`, błędne
wartości, prawdziwe zera oraz zapis do fake repozytorium. Wykonano razem z
testami persystencji MQTT:

    ../HomeHub-phase3/.venv/bin/python Tests/run_offline.py --pytest-only Tests/Unit/test_sensor_missing_data.py Tests/Unit/test_sensor_persistence.py

Po rozszerzeniu normalizacji na wspólną granicę portu: 18 testów HH-10 i 5
persystencji przechodzi. Pełny runner: **223 passed, 3 failed** (HH-01/02/04
naprawiane na innych branchach), jedno ostrzeżenie starego SDK AC. Startup
i ui_smoke: PASS. Regresja prawdziwego QML sprawdza sygnał z wątku, brak danych,
neutralny kolor, rzeczywiste zero i późniejszy poprawny odczyt obu pokoi.
Nie użyto połączenia MQTT, bazy danych ani sprzętu.

## Ryzyko i rollback

Kod kliencki, który traktował `0` jako brak danych, musi teraz obsługiwać `None`;
to jest zamierzona zmiana semantyki. Zmieniono typ sygnału Qt, lecz nie zmieniono
istniejących wartości klimatyzacji ani pogody. Wycofanie wymaga revertu commita
w osobnym PR; brak migracji danych i zmian produkcyjnej konfiguracji.
