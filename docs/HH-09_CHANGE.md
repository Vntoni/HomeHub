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

- Backend sprawdza cache, a następnie pobiera świeży odczyt przed pierwszym
  poleceniem SDK. OFF, UNKNOWN, brak trybu lub błąd odczytu blokują zapis.
  Wyłączenie pilotem widoczne w tym odczycie kończy się błędem bez setterów.
- QML zachowuje tryb odczytany przy otwarciu (`loadedMode`). Dla `OFF` przycisk
  „Zastosuj” jest wyłączony, a ustawienia można zmienić dopiero po włączeniu
  dedykowanym przełącznikiem zasilania.
- Zmiana trybu w formularzu nie omija blokady. Kolejne sygnały stanu aktualizują
  blokadę bez nadpisywania edytowanych ustawień; widoczny tekst wyjaśnia powód.
- Wyłączenie klimatyzatora z popupu, gdy był włączony przy otwarciu, pozostaje
  dozwolone; `OFF` jest wtedy świadomą zmianą zasilania.

## Weryfikacja

Nowe scenariusze obejmują odrzucenie zapisu dla wyłączonego AC bez wywołania
setterów oraz zachowanie możliwości wyłączenia urządzenia z trybu włączonego.
Headless QML sprawdza `loadedMode == OFF` i wyłączony przycisk „Zastosuj”.

Regresje świeżego odczytu odtworzono: 6 failed, 1 passed na wcześniejszej poprawce
sprawdzającej wyłącznie cache. Po uzupełnieniu: 37/37 testów guard/panel/fan PASS.
Pełny `Tests/run_offline.py`: **227 passed, 2 failed** (HH-03/04 na osobnych
branchach). Startup QML, ui_smoke z blokadą przycisku oraz ac_power_smoke: PASS.
Testy działają offline poza sandboxem ograniczającym Qt/NEON. Błąd pluginu
offscreen w pierwszej próbie usunięto w testowym venv i powtórzono cały runner.

## Ryzyko i rollback

Zmiana blokuje zapis ustawień przy OFF lub niepotwierdzonym trybie; dedykowane
włączanie pozostaje bez zmian. Dodaje jeden odczyt w ramach istniejącego limitu
45 s. Chmura może opóźniać raportowanie, a pilot może zmienić stan już po odczycie;
API nie oferuje atomowego „zapisz tylko jeśli ON”, więc tego wyścigu nie da się
wyeliminować samą kontrolą po stronie HomeHub. Sprzęt pozostaje do testu na Pi.
Wycofanie wymaga revertu tego commita w osobnym PR; nie ma migracji danych ani
zmiany konfiguracji produkcyjnej. Sprzętu nie sterowano.
