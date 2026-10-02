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

Ręczny przycisk korzysta z tej samej ścieżki. W trybie demo i testach można
zmienić `deviceRefreshIntervalMs` bez zmiany kodu backendu.

## Testy

Smoke test QML sprawdza wartość interwału 900 000 ms. Kontrola składni i
integralności przechodzi lokalnie. Pełny headless QML pozostaje do ponownego
uruchomienia po odblokowaniu runnera Qt; nie wykonywano odczytów z fizycznych
urządzeń.
