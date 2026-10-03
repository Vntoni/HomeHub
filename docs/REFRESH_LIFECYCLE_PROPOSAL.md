# Decyzja przed dalszą zmianą architektury: HH-07, HH-11, HH-12, AUTO-01

**Decyzja użytkownika: wariant A zatwierdzony w bieżącej rozmowie.**

## Zatwierdzone zachowanie

- AC po błędzie potwierdzenia zachowuje ostatni potwierdzony stan i pokazuje błąd.
- Bojler i grzejniki po błędzie odczytu zachowują dane z oznaczeniem nieaktualności;
  poprawny odczyt usuwa błąd (decyzja użytkownika z bieżącej rozmowy).
- Ustawienia wyłączonego AC są blokowane (HH-09).
- Brak pomiaru sensora jest „brakiem danych”; nie powstaje sztuczny zapis zera (HH-10).
- Odczyty urządzeń co 900 s, osobno od natychmiastowego potwierdzania komendy.

## Dlaczego potrzeba wspólnej decyzji

Obecnie QtHomeBackend chroni lockiem tylko komendy. `init_all`, przycisk refresh
i metody serwisów mogą czytać równolegle. `CozyTouchHeaterAdapter` deleguje do
`asyncio.to_thread`, a klient Atlantic współdzieli listę urządzeń i token między
pokojami. Timeout asyncio nie zatrzymuje wykonującego się wątku: następna komenda
może wejść, zanim poprzednia faktycznie skończy. Sam timer 900 s zwiększyłby ten
problem. `build_backend` nie zwraca uchwytu taska pogody ani repozytorium do
zamknięcia; błąd startu przed utworzeniem backendu może pozostawić zasoby.

## Wariant A — wspólne zarządzanie operacjami i zasobami (zalecany)

Bez nowych frameworków. Mały komponent w App odpowiada za trwające operacje,
a obiekt zasobów aplikacji za ich zamknięcie. Adaptery urządzeń pozostają.

1. Odczyt ręczny, odczyt po komendzie i timer korzystają z tej samej ścieżki.
   Klucze obejmują urządzenie oraz współdzielony klient Atlantic. Powtórny odczyt
   dołącza do trwającego lub jest pomijany, bez nieograniczonej kolejki.
2. Zadanie operacji pozostaje zarejestrowane aż do rzeczywistego końca transportu.
   Timeout żądania UI pokazuje błąd/niepewność, lecz nie zwalnia możliwości drugiej
   sprzecznej komendy podczas działającego wątku. Żadnych automatycznych powtórek
   zapisu. Po późnym zakończeniu następuje kontrolowany odczyt i publikacja stanu.
3. Każde urządzenie ma ostatni kompletny snapshot odczytu, czas potwierdzenia
   i flagę nieaktualności. Błędny lub częściowy odczyt zachowuje snapshot i ustawia
   błąd; QML widzi aktualność niezależnie od zasilania. Sukces usuwa oznaczenie.
4. Odczyty niezależnych klientów są odseparowane: awaria pierwszego AC nie blokuje
   drugiego ani bojlera. Anulowanie jest propagowane i nie staje się sukcesem.
5. Zasoby są rejestrowane od chwili utworzenia. Błąd częściowego startu zamyka je
   w odwrotnej kolejności. Zachowujemy dotychczasową politykę wymaganych integracji
   na starcie; nie wprowadzamy samodzielnie trybu częściowo działającej aplikacji.
6. Shutdown zatrzymuje timer i producentów MQTT/BLE/pogody, kończy przyjęte zapisy,
   zamyka klientów i pool DB, raportuje przekroczenie limitów. Obsługa SIGTERM oraz
   błędu ładowania QML korzysta z tej samej ścieżki.
7. Dopiero potem jeden timer monotoniczny odczytów co 900 s; restart nie nadrabia
   zaległych cykli. Timer nie tworzy nowych klientów MQTT/BLE i nie wysyła komend.

Konsekwencja: zmiany obejmą App, QtHomeBackend, composition root i View/main.py,
więc wymagają review architektury przed implementacją zgodnie z zasadą użytkownika.
To większy zakres niż pojedyncza poprawka adaptera, ale jeden kontrakt obejmie
wszystkie źródła odświeżenia. Ryzyko regresji: kolejność sygnałów QML i zamykania.

## Wariant B — osobne poprawki istniejących ścieżek

Dodać locki/statusy osobno w każdym serwisie, osobne uchwyty tasków w backendzie
i ręczny cleanup każdego kroku kompozycji. Mniejsza pojedyncza zmiana, więcej PR-ów
i powielona logika. Każde nowe wejście (timer, odczyt po komendzie, refresh) musi
oddzielnie przestrzegać wszystkich blokad; trudniej dowieść bezpieczeństwa późnego
zakończenia wątku i współdzielonego klienta Atlantic. Nadal potrzebne są wszystkie
poniższe testy; wariant nie uzasadnia wcześniejszego uruchomienia timera.

## Podział PR-ów i testy akceptacyjne

1. `fix/operation-lifecycle` (HH-12): wątek zablokowany Eventem, timeout/cancel,
   druga komenda i refresh; brak nakładania do zwolnienia Eventu. Spóźniony wynik
   nie nadpisuje nowszego snapshotu. Blokada wspólnego klienta między pokojami.
2. `fix/device-freshness` (HH-07): online → 503 → powrót; ostatnie dane zachowane,
   błąd widoczny na realnym QML i usuwany po sukcesie; pierwszy AC błędny, drugi
   poprawny. Niekompletna odpowiedź nie jest kompletnym potwierdzeniem.
3. `fix/application-shutdown` (HH-11): fake zasoby i awaria po każdym kroku startu,
   dwukrotny stop, SIGTERM oraz błąd QML w osobnym procesie, końcowy zapis do DB;
   brak pozostawionych tasków/klientów, jawny timeout niekończącego się transportu.
4. `feature/periodic-device-refresh` (AUTO-01): kontrolowany zegar, dokładnie jeden
   cykl po 900 s, zmiana pilotem odzwierciedlona w QML, zbieżność trzech źródeł
   odczytu, wolne API, stop i wznowienie; zero metod sterujących.

Implementacja wariantu A została autoryzowana. Propozycja nie scala istniejących PR-ów,
nie aktywuje produkcyjnego deployu i nie zmienia konfiguracji urządzeń.
