# HH-04 — działający odczyt pogody

Druga definicja OpenMeteoAdapter przesłaniała pierwszą i odwoływała się do
niezaimportowanego httpx. Odczyt zwracał None nawet dla poprawnej odpowiedzi.
Pozostawiono jedną, dotychczas aktywną implementację async i dodano jawny import
już zadeklarowanej zależności httpx. Usunięto nieużywany executor i duplikaty.

Odtworzenie: python Tests/run_offline.py --pytest-only Tests/Unit/test_weather_refresh.py.
Przed zmianą: 5 failed, 1 passed. Po zmianie: 6 passed, obejmujące poprawne
mapowanie, HTTP 503, timeout, brak pól, błąd dekodowania i anulowanie pollingu.

Pełna suite: 206 passed, 3 failed (niezmienione HH-01, HH-02, HH-03), plus
ostrzeżenie o nieoczekiwanej coroutine w wadliwym kontrakcie HH-02.
Startup demo i UI smoke: PASS. Nie pominięto czerwonych regresji.
Składnia i integralność: PASS. Transport HTTP jest fake; nie wykonano
połączenia z API pogody ani produkcyjną bazą.

Ryzyko: format odpowiedzi API, jednostki i timestamp; sprawdzone na fake
odpowiedzi. Ustawienia i interwał pollingu pozostają bez zmian.
Rollback: revert commita; brak migracji/zmian danych. Baza PR:
audit/test-environment. Bez wdrożenia ani automatycznego merge.
