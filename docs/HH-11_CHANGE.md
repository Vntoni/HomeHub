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

Zamykanie jest współdzielonym zadaniem: kolejne wywołania czekają na ten sam
wynik. Błędy są zbierane i zgłaszane po próbie zamknięcia pozostałych zasobów.
Obsługa sensorów poprzedza DB, preferuje `aclose()` (kontrakt opróżniania zapisów
z HH-03/06). Synchronizacyjne `close()` działa poza wątkiem Qt.

`App.lifecycle.build_with_resources` rejestruje zasoby od chwili utworzenia i
zwalnia je także po błędzie/anulowaniu startu. Kompozycja rejestruje DB, sesję
Airstage i powstające adaptery MQTT. SIGTERM i błąd załadowania QML przechodzą
przez `backend.shutdown()`. Zadanie inicjalizacji również ma właściciela.

MQTT sprawdza zamknięcie po blokującym connect, nie rozpoczyna wtedy pętli
sieciowej i jawnie zgłasza timeout, jeśli wątek nie kończy się w limicie.

## Testy

Odtworzono regresję: błąd jednego `close()` przerywał kolejne zamknięcia, a
kontrakt `SensorService.aclose()` był pomijany. Test kolejności zamykania przed
poprawką: FAIL, po poprawce: PASS. Dodano dziewięć testów scope startupu na
fake zasobach, test connect/close MQTT oraz osobne procesy z rzeczywistym Qt
dla SIGTERM i błędu QML. Produkcyjna kompozycja nie jest uruchamiana w testach;
guard offline nadal blokuje jej import.

Ryzyko: integracja z odrębnymi PR-ami HH-03/06 wymaga wspólnego testu końcowego
zapisu do DB. Ta gałąź sama nadal zawiera bazowe błędy HH-03 i HH-04. Nie jest
samodzielnym pakietem produkcyjnym.

Nie wykonywano połączeń z fizycznymi urządzeniami.

Wyniki: pełny pytest **246 PASS, 2 FAIL (bazowe HH-03/04)**; dodatkowy później
dopisany test MQTT **1 PASS**. Startup i interakcje QML: PASS. AC readback,
SIGTERM i błąd QML: PASS w celowanym ponowieniu po powrocie problemu pluginu
offscreen w środowisku macOS. Zabezpieczenie offline: PASS.
