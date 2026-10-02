# HH-11 — kontrolowane zamykanie aplikacji

## Problem

Skład główny uruchamiał polling pogody i adaptery MQTT poza wspólnym cyklem
życia backendu. Zamknięcie okna zatrzymywało monitor pralki, ale nie posiadało
jednego rejestru dla zadań w tle i zasobów wymagających `close()`.

## Zmiana

`QtHomeBackend` udostępnia rejestr zadań i zasobów aplikacji. Przy zamykaniu:

1. koordynator kończy aktywne operacje urządzeń,
2. zatrzymywany jest monitor pralki,
3. anulowane i dołączane są zadania w tle, w tym polling pogody,
4. zamykane są sensory MQTT i pozostałe zasoby zarejestrowane w składzie.

Zamykanie jest idempotentne. `ZigbeeSensorAdapter.close()` rozłącza klienta
MQTT i czeka krótko na zakończenie jego prywatnego wątku. Nie zmienia to
mechanizmu ponownego łączenia podczas normalnej pracy.

## Testy

Dodano test rejestracji zadania i zasobu oraz drugiego, bezpiecznego wywołania
`shutdown()`. Kod przechodzi kontrolę składni i `git diff --check`.
Testy wymagające Qt pozostają do uruchomienia, gdy środowisko testowe będzie
dostępne; obecny runner jest blokowany przez limit wykonawczy.

Nie wykonywano połączeń z fizycznymi urządzeniami.
