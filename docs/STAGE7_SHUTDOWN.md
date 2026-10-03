# Etap 7 — poprawne zamykanie Qt/qasync

## Problem i odtworzenie

Użytkownik zgłosił `RuntimeError: Event loop stopped before Future completed`
przy zamykaniu wersji na Pi. `Restart=no` zatrzymało ponowne otwieranie okna,
ale pozostawiło wyjątek i ryzyko niedokończonego zwalniania zasobów.

`View/main.py` wcześniej uruchamiał Qt osobno dla budowania backendu, działania
okna i `backend.shutdown()`. Qt.quit/SIGTERM kończył pętlę przed cleanup,
a kolejne żądanie wyjścia mogło przerwać ponowne run_until_complete.

Regresja na rzeczywistym Qt z atrapą wolnego aclose: SIGTERM rozpoczyna
zamykanie, a kolejne app.quit przychodzi podczas oczekiwania na zasób.
Przed naprawą `Tests/run_offline.py --smoke-only shutdown_smoke` zwracało
exit 1 i dokładnie wskazany RuntimeError z run_until_complete w View/main.py.
To potwierdza błąd tej ścieżki kodu; nie dowodzi, że drugi sygnał był jedynym
wyzwalaczem konkretnego zdarzenia na Pi (log użytkownika nie zawierał pełnego stosu).

## Poprawka

Start, oczekiwanie na zamknięcie i cleanup są teraz jedną korutyną wykonaną
przez pojedyncze run_until_complete. ShutdownRequest przechwytuje QEvent.Quit,
zamknięcie głównego okna, Qt.quit oraz SIGTERM i ustawia asyncio.Event.
Okno zostaje ukryte, ale pętla nadal wykonuje backend.shutdown(). Ponowne
żądania nie przerywają sprzątania. qasync kończy Qt po zakończeniu korutyny.

Zachowano kolejność zamykania w backendzie, odprowadzanie zapisów sensorów,
koordynator operacji i zgłaszanie rzeczywistych błędów cleanup. Nie tłumimy
wyjątku tekstowym filtrem ani nie wymuszamy exit(0). Przy błędzie ładowania QML
backend również jest zamykany. Handler SIGTERM jest przywracany.

Nie zmieniono Restart=no, sterowania urządzeniami ani konfiguracji MQTT.
Podczas startu bez okna żądanie wyjścia jest zapamiętane; jeśli build_backend
jeszcze trwa, cleanup następuje po jego zakończeniu. Nie dodano przerywania
w połowie inicjalizacji transportów ani nowych limitów ich timeoutów.

## Walidacja

Lokalnie: **351 passed + 8/8 smoke PASS**, guard offline PASS, kontrola
składni/integralności i git diff --check PASS. Bez sieci i prawdziwych urządzeń.

Scenariusze zakończenia używają prawdziwej pętli Qt i sprawdzają:

- SIGTERM, zamknięcie przez window manager i Qt.quit z QML;
- powtórne wyjście w trakcie wolnego aclose;
- anulowanie zarejestrowanego zadania i dokładnie jednokrotne zamknięcie zasobów;
- brak aktywnych operacji i ukończone shutdown;
- błąd jednego zasobu nadal zwraca ExceptionGroup, a następny zasób się zamyka;
- błąd ładowania QML nadal zwalnia backend.

Osiem smoke obejmuje także dotychczasowy start demo, interakcje panelu i AC
readback. Test zgłaszania błędu cleanup ma PASS tylko gdy błąd faktycznie
propaguje, nie gdy aplikacja go ukryje. Testy włączone do istniejącego runnera.

W workflow dodano `Test shutdown offline with Pi Qt and qasync` przed buildem
i zatrzymaniem produkcji. Na Pi wykona pięć scenariuszy zamykania z demo,
offscreen i OfflineGuard. Krok należy tylko do deployu z zaufanego main;
PR-y nadal testują się na runnerze GitHub, nie na produkcyjnym Pi.

## Granice potwierdzenia i wdrożenie

Podczas przygotowania PR nie wykonano testu na fizycznym Pi ani zamknięcia
działającej aplikacji. Zielone CI nie zastępuje sprawdzenia z jego wersją
Qt/qasync ani prawdziwymi zasobami. Po zatwierdzeniu merge krok Pi musi przejść
przed podmianą aplikacji. Nie oznaczać etapu sprzętowego jako PASS wcześniej.

Ręczny odbiór po wdrożeniu: zamknąć okno raz, sprawdzić brak nowego tracebacku,
status procesu oraz brak samoczynnego otwarcia. Ponownie uruchomić aplikację
przez systemctl --user start bazadomowa. Test nie wymaga zmiany stanu urządzeń,
ale uruchomienie produkcji nawiązuje jej zwykłe połączenia. Oddzielnie sprawdzić
zatrzymanie usługi, jeśli użytkownik zatwierdzi okno przerwy.

Ryzyko regresji: przechwytywanie zdarzeń zamknięcia zależne od Qt/platformy;
rzeczywisty transport może nadal zgłosić własny timeout podczas cleanup.
Nie należy go ukrywać. Powrót kodu przez revert commita po decyzji użytkownika;
Restart=no pozostaje, nie ma migracji danych. Nie rozpoczynamy etapu audio.
