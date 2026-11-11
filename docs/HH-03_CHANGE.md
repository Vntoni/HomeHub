# HH-03 — zapis pomiarów z wątku MQTT

Callback MQTT wywoływał asyncio.get_event_loop() we własnym wątku. RuntimeError
był ignorowany, więc pomiar nie trafiał do repozytorium. Odtworzenie:
python Tests/run_offline.py --pytest-only Tests/Unit/test_sensor_persistence.py.
Przed poprawką: 5 niezaliczonych testów.

SensorService zapamiętuje pętlę właściciela podczas konstrukcji i używa
run_coroutine_threadsafe. Śledzi przyjęte zapisy, raportuje błędy bez treści DSN
i zamyka się z limitem 5 s. Backend wywołuje zamknięcie serwisu. Composition
tworzy serwis przed uruchomieniem wątków MQTT, aby pierwszy callback nie został
pominięty. Nie zmieniono walidacji payloadów ani zachowania urządzeń.

Weryfikacja po zmianie:

- 8/8 testów persystencji, kontraktu repozytorium i lifecycle pralki przechodzi.
- Pełna suite: 205 passed, 3 failed. Nadal czerwone HH-01, HH-02, HH-04
  dotyczą osobnych napraw; nie zastosowano skip/xfail.
- Startup demo i UI smoke: PASS, 3 rozdzielczości; bez sprzętu.
- Składnia i integralność projektu: PASS.

Ograniczenia: brak testu rzeczywistego brokera/DB na Pi. Brak trwałego bufora
offline; błąd DB oznacza jawny błąd zapisu, a nie automatyczne ponowienie.
Limit zamknięcia może anulować zaległe zapisy i raportuje to. Rozmiar kolejki
oraz polityka utrwalania przy długiej awarii pozostają częścią HH-11.

PR jest niezależny od napraw AC i pogody, bazuje na audit/test-environment.
Rollback: revert commita tej naprawy; brak migracji danych i zmian konfiguracji.
Revert przywróci także dotychczasowy błąd, dlatego nie jest zalecanym sposobem
radzenia sobie z awarią DB. Nie wykonywano wdrożenia.
