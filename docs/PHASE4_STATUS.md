# Faza 4 — wspólna weryfikacja napraw

Gałąź `audit/integration` łączy naprawy wywodzące się z wersji
`2552c9b51cc77604af3e3e3c861ad3bd11e5009b` z 1 października.
Nie wykonano merge do main, wdrożenia ani sterowania rzeczywistymi urządzeniami.
Pierwotny katalog HomeHub z niezacommitowaną pracą pozostaje bez zmian.

## Zrealizowany zakres

- HH-01/02/09: stan AC z potwierdzonego odczytu, readback po komendzie,
  zachowanie ostatniego stanu po błędzie i blokada ustawień wyłączonego AC.
- HH-03/05/06/10: zapis MQTT na właściwej pętli, walidacja wiadomości,
  reconnect i zamykanie połączenia; brak pomiaru nie tworzy sztucznego zera.
- HH-04/08: aktualizacja pogody i poprawna interpretacja wyniku Atlantic.
- HH-07/12: spójne snapshoty bojlera/grzejników, oznaczanie nieaktualności,
  wspólna koordynacja operacji zgodnie z zatwierdzonym wariantem A.
- HH-11: cleanup przy błędzie startu i QML, SIGTERM, zamykanie wszystkich
  zasobów mimo błędu pojedynczego zasobu, zapis sensorów przed zamknięciem DB.
- AUTO-01: odczyt urządzeń co 15 minut; cykle ręczne i automatyczne współdzielą
  trwającą operację. Komendy nadal mają własny odczyt potwierdzający.
- HH-13: CI uruchamia izolowane testy i QML dla PR do każdej gałęzi,
  archiwizuje wyniki także po błędzie. Deploy ma warunek push do main.
- HH-14: poprawiona dokumentacja i przykłady konfiguracji, test kolejności
  wyszukiwania .env i constraints bezpośrednich zależności środowiska testowego.

Przyczyny, odtworzenie, testy i ryzyko poszczególnych zmian opisują
`HH-01_CHANGE.md` do `HH-14_CHANGE.md`
oraz `AUTO-01_CHANGE.md`.

## Integracja i walidacja

Zmiany z osobnych branchy przeniesiono na gałąź integracji, zachowując PR-y
cząstkowe i ich historię. Rozwiązano konflikty w obsłudze MQTT, brakujących
pomiarach i zamykaniu zasobów. Test reconnect otrzymał kompletny pomiar
temperatury i wilgotności zgodny z kontraktem HH-10; testów odrzucania
niekompletnych pomiarów nie usunięto.

Dodatkowy test `test_integrated_shutdown.py` sprawdza wspólnie SensorService,
backend i repozytorium: ostatni callback podczas zatrzymywania sensora musi
zostać zapisany przed zamknięciem DB. Drugie shutdown nie powtarza operacji.

Lokalnie, macOS/Python 3.12: **338 passed**, kontrola składni i integralności
PASS, `pip check` PASS, **5/5 smoke QML PASS** (start, interakcje/timer,
potwierdzenie AC, SIGTERM, błąd ładowania QML). Guard potwierdził blokowanie
7 niedozwolonych operacji. Logi lokalne są w `test-results/`.

[GitHub Actions dla commita 6dd95d9](https://github.com/Vntoni/HomeHub/actions/runs/37126496245)
potwierdziło na Linux/Python 3.11.16: **338 passed, 5/5 smoke QML PASS**,
kontrolę zależności, składni i integralności PASS. Wyniki zapisano jako artefakt.
Job Build & Deploy on RPi5 został **SKIPPED**. Runner zgłosił ostrzeżenie
o Node 20 w upload-artifact@v4; przesłanie artefaktu zakończyło się powodzeniem.
Po tym przebiegu uzupełniono wyłącznie dokumentację; aktualne checki są w PR.

Wyniki wcześniejszych PR-ów cząstkowych zawierają znane błędy z innych,
nieobecnych tam napraw. Miarodajnym wynikiem całego zestawu jest integracja.
Nie pomijano regresji przez skip/xfail.

## PR-y do przeglądu

Osobne draft PR-y #1–14 obejmują bazę testową i naprawy HH-01–12/AUTO-01.
[PR #15](https://github.com/Vntoni/HomeHub/pull/15) obejmuje CI,
[PR #16](https://github.com/Vntoni/HomeHub/pull/16) konfigurację i zależności.
[Wspólny draft PR #17](https://github.com/Vntoni/HomeHub/pull/17)
stanowi kandydat do review całego zestawu;
nie należy scalać automatycznie ani kolejno wdrażać niekompletnych PR-ów.

## Granice weryfikacji i dalsza decyzja

Testy używają fake transportów i blokady sieci oraz produkcyjnej konfiguracji.
Nie potwierdzają działania fizycznego AC, Atlantic, Ariston, BLE, brokera MQTT
ani produkcyjnej bazy. Qt sprawdzono w trybie headless.

HH-14 pozostaje częściowo otwarty: produkcyjny lock wymaga odczytu wersji
istniejącego środowiska Pi i sprawdzenia builda ARM. Nie zastąpiono go listą
pakietów macOS; produkcyjnych zależności ani .env nie zmieniano.

Przed wdrożeniem potrzebne są review użytkownika, zatwierdzenie przejścia do
fazy 5 i izolowane testy na Pi według `RASPBERRY_PI_TESTING.md`. Istniejący
deploy nadal wymienia katalog aplikacji; jego rollback wymaga pracy w fazie 5.
Ustawień ochrony main nie zmieniano. Fazy 5 i 6 ani funkcji AI nie rozpoczęto.

Zakres implementacji i integracji offline fazy 4 jest zakończony i gotowy do
przeglądu. Nie oznacza to zatwierdzenia produkcyjnego wdrożenia ani zamknięcia
niezweryfikowanej części HH-14 dotyczącej Pi.
