# HH-09 — blokada ustawień wyłączonego klimatyzatora

## Problem i odtworzenie

Popup ustawień AC mógł przyjąć temperaturę, tryb i opcje dodatkowe, gdy
urządzenie było już w trybie `OFF`. Ścieżka zapisu kończyła się wtedy poleceniem
`turn_on`, więc zapis ustawień mógł niejawnie uruchomić klimatyzator.

Regresję odtwarza `Tests/Unit/test_panel_commands.py`: ustawiamy fake AC w
`OFF`, wywołujemy `apply_ac_settings(..., "HEAT", ...)` i sprawdzamy brak
wywołań zapisu SDK oraz komunikat błędu. Przed poprawką zapis przechodził i
urządzenie zmieniało tryb na `HEAT`.

## Zmiana

- Backend sprawdza bieżący odczyt trybu przed pierwszym poleceniem SDK.
  Wyścig ze zdalnym wyłączeniem po otwarciu popupu kończy się błędem bez zapisu.
- QML zachowuje tryb odczytany przy otwarciu (`loadedMode`). Dla `OFF` przycisk
  „Zastosuj” jest wyłączony, a ustawienia można zmienić dopiero po włączeniu
  dedykowanym przełącznikiem zasilania.
- Wyłączenie klimatyzatora z popupu, gdy był włączony przy otwarciu, pozostaje
  dozwolone; `OFF` jest wtedy świadomą zmianą zasilania.

## Weryfikacja

Nowe scenariusze obejmują odrzucenie zapisu dla wyłączonego AC bez wywołania
setterów oraz zachowanie możliwości wyłączenia urządzenia z trybu włączonego.
Headless QML sprawdza `loadedMode == OFF` i wyłączony przycisk „Zastosuj”.

Wykonanie testów Qt poza sandboxem jest wymagane, ponieważ lokalny interpreter
PySide6 przerywa import z powodu wykrywania NEON. Próba sandboxowa zakończyła się
kodem -6 przed kolekcją; nie jest to wynik testów HomeHub. Po odblokowaniu
środowiska należy uruchomić `Tests/run_offline.py` oraz istniejący `ui_smoke.py`.

## Ryzyko i rollback

Zmiana blokuje tylko zapis ustawień zaawansowanych, gdy ostatni odczyt trybu jest
`OFF`; dedykowane włączanie pozostaje bez zmian. Jeżeli SDK zwraca chwilowo
nieprawidłowy tryb, operacja kończy się bezpiecznym błędem i wymaga odświeżenia.
Wycofanie wymaga revertu tego commita w osobnym PR; nie ma migracji danych ani
zmiany konfiguracji produkcyjnej. Sprzętu nie sterowano.
