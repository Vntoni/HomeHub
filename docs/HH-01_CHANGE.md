# HH-01 — potwierdzanie zasilania klimatyzacji

Przyjęcie zapisu przez API zmieniało cache SDK, nawet gdy urządzenie nadal
pozostawało OFF. Po błędzie odczytu dashboard publikował ten optymistyczny stan.
Użytkownik zatwierdził zachowanie ostatniego potwierdzonego stanu z komunikatem
błędu. Adapter przechowuje teraz potwierdzony tryb osobno od cache zapisu.
Niepełna odpowiedź również nie nadpisuje potwierdzonego stanu.

Po jednej komendzie zasilania backend wykonuje do 4 odczytów, z odstępami 2 s,
w istniejącym limicie operacji 45 s. Porównuje odczyt z żądaniem. Nie ponawia
polecenia sterującego. Błąd lub brak zgodności pozostawia widoczny błąd, a kolejny
poprawny odczyt aktualizuje przełącznik. Ta zmiana nie dodaje harmonogramu
15-minutowego; AUTO-01 pozostaje osobnym zadaniem po stabilizacji lifecycle.

Odtworzenie i testy:

- Testy adaptera przed naprawą: oba scenariusze ON/OFF nie przechodziły.
- Po naprawie: 17/17 testów kontraktu AC, potwierdzonego stanu i readbacku
  przechodzi. Sprawdzono opóźnione potwierdzenie, niezgodność, UNKNOWN,
  timeout/wyjątek, anulowanie i ponowny odczyt.
- Pełna suite: 218 passed, 2 failed (HH-03 i HH-04 z osobnych branchy).
- Startup demo i UI smoke: PASS. Smoke czeka na rzeczywiste zakończenie zapisu
  w QML zamiast zakładać, że 250 ms zawsze wystarcza na obciążonym hoście.
- Nowy ac_power_smoke: PASS; realny QML, realne SDK, niezależny fake urządzenia,
  kliknięcie, pending, błąd refresh, ponowna publikacja, odzyskanie, OFF i drugi pokój.
- Składnia i integralność: PASS. Bez zmian produkcyjnego QML i konfiguracji.

Komenda pełna: python Tests/run_offline.py. Runner wykonuje również
Tests/ac_power_smoke.py i zapisuje log do test-results/ac_power_smoke.log.
Wynik całości pozostaje niezerowy ze względu na HH-03/HH-04; bez xfail/skip.

Zależność: PR do fix/ac-refresh-contract (HH-02). Nie łączyć przed review
kontraktu SDK. Wersja na Pi i zachowanie prawdziwej chmury wymagają sprawdzenia
przed wdrożeniem. ON oznacza zasilanie, nie aktywną pracę sprężarki.
Po wyczerpaniu prób nie ma ciągłego pollingu; odczyt może przyjść z ręcznego
odświeżenia, kolejnej operacji lub przyszłego AUTO-01. Nie zmieniono sekwencji
ustawień temperatury z OFF (HH-09) ani cache pozostałych parametrów.

Ryzyko regresji: starsze SDK, zmiana z innego kontrolera, opóźnienie chmury
przekraczające okno potwierdzenia. Rollback przez revert tego commita,
z pozostawieniem HH-02; bez migracji. Nie wykonano sterowania sprzętem ani deployu.
