# HH-05 — odrzucanie wadliwych pomiarów MQTT

## Problem i odtworzenie

`ZigbeeSensorAdapter._on_message` podmieniał cache przed sprawdzeniem struktury
JSON i wartości. Lista, null, nieliczbowa temperatura lub nieskończoność mogły
uszkodzić stan albo przerwać callback przy konwersji w SensorService/QML.
Wyjątek odbiorcy callbacku także wychodził do pętli MQTT.

Regresję odtwarza `Tests/Unit/test_mqtt_payload.py`: po poprawnym pomiarze
dostarcza błędny payload, sprawdza cache i obsługę następnego dobrego pomiaru.
Przed poprawką: **17 failed, 7 passed**.

## Zmiana

- Najpierw dekodowanie i walidacja obiektu oraz wszystkich obecnych pól
  liczbowych, dopiero potem wymiana cache i callback.
- Odrzucenie null, bool, nieliczbowych wartości, NaN/inf, wadliwego JSON/UTF-8.
- Jawny log błędu; awaria odbiorcy nie kończy obsługi następnych wiadomości.
  Log nie zawiera payloadu ani tekstu wyjątku, który mógłby ujawnić dane.
- Zachowano obsługę częściowych wiadomości, liczbowych stringów, dodatkowych
  pól i prawdziwego zera. Nie wprowadzono arbitralnych zakresów temperatur.

## Weryfikacja

    ../HomeHub-phase3/.venv/bin/python Tests/run_offline.py --pytest-only Tests/Unit/test_mqtt_payload.py
    ../HomeHub-phase3/.venv/bin/python Tests/run_offline.py
    ../HomeHub-phase3/.venv/bin/python Tests/check_integrity.py

Regresje: **24 passed**. Pełny pytest: **223 passed, 4 failed** (HH-01–HH-04,
naprawiane na osobnych branchach), jedno ostrzeżenie starej ścieżki SDK AC.
Startup QML i pełny ui_smoke: PASS. Składnia/integralność: PASS.
Fake klient i wyłączony start wątku; brak połączenia z brokerem lub sprzętem.
Logi lokalne: test-results/. CI tej gałęzi nie uruchamia się przy PR do audit/....

## Ryzyko i ograniczenia

Czujnik, który celowo wysyła null w polu liczbowym, straci całą taką wiadomość,
a ostatni poprawny cache zostanie zachowany. Jest to odrzucenie błędnego pomiaru,
nie potwierdzenie jego świeżości. Status jakości/stale i brak danych zamiast zera
pozostają osobnymi decyzjami HH-07/HH-10. Puste/częściowe poprawne payloady nadal
zastępują cache zgodnie z dotychczasowym kontraktem. Brak walidacji zakresów
specyficznych dla modelu sensora do czasu potwierdzenia jego specyfikacji.
Wyjątek callbacku jest raportowany, ale wiadomość nie jest ponawiana ani buforowana.

Branch `fix/mqtt-payload-validation`, baza testowa z commita 1 października.
Bez merge i deployu. Wycofanie po przyszłej integracji: revert tego commita
w nowym PR; brak migracji danych i zmian produkcyjnej konfiguracji.
