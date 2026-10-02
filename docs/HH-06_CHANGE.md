# HH-06 — ponowienie początkowego połączenia MQTT

## Przyczyna i odtworzenie

Pierwszy `Client.connect()` wykonywany przez `ZigbeeSensorAdapter._run`
nie obsługiwał odmowy połączenia. Wątek kończył się wyjątkiem, zanim wszedł
w `loop_forever()`, więc uruchomienie brokera później nie przywracało pomiarów.
Brakowało również możliwości zakończenia wątku przy zamykaniu aplikacji.

Test z fake klientem odmawia dwukrotnie, następnie przyjmuje połączenie
i dostarcza pomiar. Pierwsze 9 regresji przed poprawką: **9 failed**.

## Poprawka

- Początkowe błędy OSError są ponawiane po 1, 2, 4, 8… sekundach, do 60 s.
  Oczekiwanie można przerwać sygnałem stop. Kolejne reconnecty obsługuje
  istniejąca pętla Paho z tym samym ograniczeniem opóźnienia 1–60 s.
- Subskrypcja następuje wyłącznie po udanym CONNACK. Brak brokera i zerwanie
  połączenia są logowane; `is_online()` oznacza połączenie brokera, nie świeżość
  pomiaru czujnika. Nie zmieniono obecnego kontraktu QML sensorów.
- `close()` zatrzymuje retry, rozłącza klienta i oczekuje do 5 s na jego wątek.
  Brak zakończenia jest jawnie zgłaszany jako TimeoutError.
- SensorService zamyka producentów poza pętlą UI, a następnie kończy przyjęte
  zapisy HH-03. Błąd zamknięcia jednego sensora nie pomija pozostałych.

## Weryfikacja

    ../HomeHub-phase3/.venv/bin/python Tests/run_offline.py

11 testów reconnect/shutdown: PASS (w tym dwa dodatkowe przypadki zamknięcia
podczas connect i późnego callbacku). Pełny pytest: **216 passed, 3 failed**
(niezależne HH-01/02/04), jedno ostrzeżenie starej ścieżki SDK AC.
Startup QML i ui_smoke: PASS. Pierwsze próby Qt nie widziały lokalnego pluginu
offscreen; po usunięciu flag hidden w testowym venv powtórzenie przeszło.
Testy używają fake klienta, kontrolowanego oczekiwania i realnego wątku dla
wyścigów shutdown; brak połączenia MQTT i brak sterowania sprzętem.

## Ryzyko i ograniczenia

Zależność: branch `fix/mqtt-persistence` (HH-03). Walidacja payloadów HH-05
pozostaje osobnym PR. Pełny lifecycle DB/pogody/częściowego startu to HH-11.
Limit connect wynosi 3 s; systemowe DNS może go przekroczyć. W takim przypadku
timeout join jest logowany, nie deklarujemy wymuszonego zakończenia wątku.
Potrzebny test prawdziwego brokera na izolowanym środowisku Pi przed produkcją.
Wycofanie: revert commita w osobnym PR; brak zmian schematu lub konfiguracji.
