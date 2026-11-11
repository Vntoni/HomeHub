# HH-02 — kontrakt refresh biblioteki Airstage

Adapter traktował refresh_parameters jako coroutine bez argumentów.
W pyairstage 3.2.2 odczyt get_devices jest asynchroniczny, a przekazanie
payloadu do refresh_parameters jest synchroniczne. Dotychczasowa ścieżka
kończyła się TypeError i nieodczytanym coroutine.

Poprawka jawnie pobiera urządzenia, wybiera ID adaptera, waliduje strukturę
i przekazuje kopię payloadu do parsera SDK. Dla implementacji z coroutine
refresh_parameters zachowano wcześniejsze wywołanie asynchroniczne.
Nie aktualizowano zależności ani konfiguracji produkcji.

Testy: python Tests/run_offline.py --pytest-only Tests/Unit/test_ac_refresh_contract.py.
Przed poprawką: 6 failed, 1 passed. Po poprawce: 7 passed.
Łącznie z testami ClimateService: 160 passed.
Pełna suite: 207 passed, 3 failed (HH-01, HH-03, HH-04 poza zakresem).
Startup demo/UI smoke: PASS. Składnia i integralność: PASS.

Zastosowano realną klasę SDK 3.2.2 z fake API, dwa urządzenia, wadliwe payloady,
timeout i odzyskanie odczytu. Kontrakt starszego async SDK sprawdzono fake'iem,
nie zainstalowano każdej historycznej wersji. Wersja biblioteki na Pi wciąż
nie jest potwierdzona; jej odczyt i test sprzętowy są wymagane przed wdrożeniem.

PR bazuje na audit/test-environment. HH-01 korzysta z tej poprawki w osobnym
zależnym branchu. Rollback: revert commita, bez zmian danych. Bez merge/deployu.
