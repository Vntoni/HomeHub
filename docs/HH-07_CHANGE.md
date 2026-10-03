# HH-07 — zachowanie ostatnich danych po nieudanym odczycie

## Problem

Po błędzie odświeżenia backend zmieniał status dostępności, ale interfejs nie
rozróżniał braku nowego odczytu od aktualnych danych. Atlantic zwraca `[]` przy
błędzie, co adapter uznawał za sukces. Ariston po udanym odczycie stanu i błędzie
odczytu energii udostępniał już częściowo zmienione wartości.

Odtworzenie: `Tests/Unit/test_confirmed_snapshots.py` — trzy regresje FAIL przed
poprawką: bojler publikował 60 zamiast ostatnich 55 stopni, a grzejnik nie zgłaszał
błędu dla pustej listy lub niekompletnego urządzenia.

## Zmiana

Backend utrzymuje stan świeżości per urządzenie (`ac`, `boiler`, `heater`) i
emituje `deviceStaleChanged`. Błąd odczytu oznacza dane jako nieaktualne, a
poprawny późniejszy odczyt usuwa oznaczenie. Ostatnie wartości pozostają w
pamięci i są nadal publikowane. Adaptery bojlera i grzejnika przechowują niezmienny,
kompletny `DeviceSnapshot` z czasem potwierdzenia. Dopiero poprawny pełny odczyt
zastępuje snapshot; błąd lub częściowa odpowiedź go nie zmienia. Przed pierwszym
odczytem temperatury są nieznane (NaN), a tryb ma wartość `unknown`.

Odczyty po komendach aktualizują tę samą flagę świeżości. Timeout oczekiwania
oznacza stan niepotwierdzony. Nie powtarzamy automatycznie komend zapisu.

Karty urządzeń pokazują komunikat „Dane nieaktualne — zachowano ostatni
odczyt”. Polecenia pozostają związane z istniejącym statusem dostępności i
koordynatorem operacji.

## Testy

Dodano regresje adapterów oraz backendu dla błędu i powrotu połączenia.
Pełny pytest offline: **235 passed, 2 failed** — pozostały HH-03 i HH-04,
naprawiane na niezależnych gałęziach. Startup QML, UI smoke z zanikiem i powrotem
odczytu bojlera oraz AC readback: **PASS**, bez ostrzeżeń QML w teście interakcji.

Ryzyko regresji: odczyt Atlantic bez wymaganych pól jest teraz błędem, zamiast
potwierdzać stan wartościami zastępczymi. Kontrakty SDK zweryfikowano na fake
transportach; rzeczywiste odpowiedzi urządzeń wymagają testu na Pi.

Nie wykonywano połączeń z fizycznymi urządzeniami.
