# HH-08 — niepotwierdzone wykonanie Atlantic nie jest sukcesem

## Przyczyna i odtworzenie

`AtlanticCozytouchClient.set_capability` zwracał True po 20 odpowiedziach
UNKNOWN oraz po HTTP 201 bez identyfikatora wykonania. Panel mógł więc pokazać
sukces mimo braku potwierdzenia. Dodatkowo HTTP 401 powodował automatyczne
powtórzenie POST sterującego urządzeniem, sprzeczne z zaakceptowanym planem testów.

Fake transport odtwarza te odpowiedzi, bez połączenia z chmurą i bez oczekiwania
15 sekund. Przed zmianą: **9 failed, 10 passed** w test_atlantic_confirmation.py.

## Poprawka

Sukces wymaga teraz statusu COMPLETED (także dotychczasowe kodowania 3 i "3").
Nieznany status, wyczerpanie prób, brak ID, błąd JSON/HTTP lub timeout daje False.
Po 401 zapisu można odświeżyć uwierzytelnienie dla następnej świadomej operacji,
ale POST nie jest ponawiany. Powtórzenie GET statusu po odświeżeniu tokena działa
jak dotychczas. Nie zmieniono sposobu sterowania temperaturą ani harmonogramem.

## Testy

    ../HomeHub-phase3/.venv/bin/python Tests/run_offline.py

19 testów HH-08: PASS. Pełny pytest: **218 passed, 4 failed** (HH-01/02/03/04,
których poprawki są na osobnych branchach). Startup QML i ui_smoke: PASS.
Integralność/składnia: PASS. Mockowane HTTP i zegar; brak kont produkcyjnych,
brak urządzeń. Testy obejmują opóźnione COMPLETED, UNKNOWN/FAILED/IN_PROGRESS,
brak ID, błędny JSON, timeout, 503 i oddzielne 401 dla zapisu oraz odczytu.

## Ryzyko i ograniczenia

API, które przyjmie polecenie bez ID, będzie teraz jawnie niepotwierdzone zamiast
oznaczone jako sukces. False nie dowodzi niewykonania polecenia — użytkownik
powinien sprawdzić stan przed następną komendą. Fizyczny readback pozostaje
odrębnym etapem; COMPLETED jest potwierdzeniem API, nie pomiarem pracy grzejnika.
Problem działającego wątku po timeout asyncio nadal należy do HH-12.
Zmiana nie skraca istniejących timeoutów HTTP ani nie rozwiązuje lifecycle.

Branch `fix/atlantic-confirmation`, baza 1 października + testy. Bez merge/deploy.
Rollback po przyszłej integracji: revert commita przez PR, bez migracji danych.
