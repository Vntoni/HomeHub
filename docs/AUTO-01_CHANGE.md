# AUTO-01 — cykliczne odświeżanie urządzeń co 15 minut

## Problem

Dotychczasowy timer QML co 10 sekund wywoływał `publish_dashboard()`, które
publikuje dane z pamięci. Po zmianie stanu w chmurze panel mógł więc pokazywać
stary stan aż do ręcznego użycia przycisku „Odśwież”.

## Zmiana

Timer aplikacji ma interwał 900 000 ms (15 minut) i wywołuje
`backend.refresh_connection()`. Ta ścieżka wykonuje rzeczywiste odczyty AC,
bojlera i grzejników przez wspólny koordynator, a następnie publikuje aktualny
stan. Timer zatrzymuje się na czas odświeżania, więc cykle nie nakładają się.

Ręczny przycisk korzysta z tej samej ścieżki. Równoległe żądania dołączają do
jednego zadania odświeżania backendu. Zadanie jest rejestrowane do zamknięcia,
a po rozpoczęciu shutdown nowe odświeżania nie są przyjmowane.
W trybie demo i testach można
zmienić `deviceRefreshIntervalMs` bez zmiany kodu backendu.

## Testy

Smoke test QML sprawdza wartość interwału 900 000 ms, a ze skróconym interwałem
testowym weryfikuje faktyczny odczyt zmienionej temperatury, brak nakładania
cykli przy wolnym API, jednoczesny refresh ręczny i brak wywołań setterów.
Nie wykonywano odczytów z fizycznych urządzeń.

Pełny runner offline: **247 PASS, 2 FAIL** (bazowe HH-03/HH-04, naprawiane
na osobnych gałęziach). Wszystkie pięć procesów smoke: **PASS** — startup,
interakcje UI wraz z timerem i wolnym API, AC readback, SIGTERM oraz błąd QML.
Guard izolacji: PASS. Przed wdrożeniem potrzebna jest integracja zatwierdzonych
PR-ów i wspólny zielony przebieg, a dla zmian sprzętowych test na Pi.
