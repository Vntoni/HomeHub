# HomeHub — faza 3: testy i izolowane środowisko

## Wersja i zakres

Baza: 2552c9b51cc77604af3e3e3c861ad3bd11e5009b, 1 października 2026.
Branch: audit/test-environment, osobny worktree HomeHub-phase3. Nazwa odróżnia
go od istniejącego lokalnego audit/stabilization; tego brancha i jego
niezacommitowanych plików nie przełączano ani nie nadpisywano.

Faza 3 dodaje narzędzia testowe, przykładowe testy akceptacyjne i plan dalszego
pokrycia. Nie zmienia kodu urządzeń ani ich zamierzonego zachowania.
Testy regresyjne nowych błędów mogą być czerwone do zatwierdzenia napraw w
fazie 4. Nie dodajemy skip, xfail ani continue-on-error, żeby ukryć te wyniki.

## Stan istniejących testów

Testy bazowe wykonano przed dodaniem nowych scenariuszy: 196 passed, 18.36 s,
coverage App/Adapters/Ports/Interface: 56% (864 instrukcje, 378 niepokrytych).
Python 3.12.14 na macOS ARM; PySide6 6.8.3, qasync 0.28.0, pyairstage 3.2.2,
pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0, asyncpg 0.31.0,
httpx 0.28.1. Python 3.11/Linux pozostaje do wykonania w CI.

Pierwsze uruchomienie w sandboxie zakończyło się kodem 134 na imporcie Qt
(wykrywanie NEON), przed testami. Powtórzenie poza sandboxem zakończyło się
sukcesem. To ograniczenie lokalnego wykonania, nie odtworzony błąd HomeHub.
Poprzednie .venv-test nie odpowiadało podczas importów; utworzono niezależne
.venv, bez zmiany zależności produkcji. Kopia audytowa w /tmp nie była już
dostępna, dlatego bazę pobrano i zweryfikowano przez Git. Zawieszoną próbę
pytest ze starego venv zakończono; nie pozostawiono jej jako monitora.

W kolejnej próbie Qt nie widział offscreen: pliki pluginów miały flagę macOS
hidden. Potwierdzono różnicę między listą katalogu w Python i QDir. Usunięto
wyłącznie tę flagę w katalogu PySide6/Qt nowego .venv; końcowe testy QML przeszły.
Nie zmieniano Qt ani ustawień systemu produkcyjnego.

## Wynik końcowy fazy 3

| Sprawdzenie | Wynik |
| --- | --- |
| Autotest ochrony offline | PASS: 7 operacji zablokowanych, socketpair działa |
| Pełny pytest po dodaniu 7 testów | **199 passed, 4 failed, 7.46 s** |
| Regresje czerwone | HH-01, HH-02, HH-03, HH-04; błędy audytowanego kodu |
| Coverage tych samych 4 pakietów | 69% (864 instrukcje, 266 niepokrytych), także ścieżki testów czerwonych |
| demo_smoke | PASS; informacja Qt o podmianie czcionki Sans Serif, bez błędu startu |
| ui_smoke | PASS, 3 rozdzielczości, brak ostrzeżeń QML |
| pip check, składnia i integralność | PASS |
| YAML propozycji workflow | parsowanie PASS; nie jest to uruchomienie GitHub Actions |
| Sprzęt/Pi/realny broker/realna DB | niewykonane |

Pełna komenda zwraca kod 1. Ochrona offline nie zgłosiła nieoczekiwanego I/O
w końcowym wykonaniu testów aplikacji. Szczegóły: test-results/pytest.log,
pytest.xml, coverage.xml, demo_smoke.log, ui_smoke.log i guard_smoke.log.
Pliki są lokalnymi artefaktami, ignorowanymi przez Git. Zwiększenie coverage
nie oznacza naprawy żadnego z czterech błędów.

| Istniejący plik | Rzeczywisty zakres | Główna luka |
| --- | --- | --- |
| test_climate_service.py | delegowanie, pokoje, parametry, flagi | mocki nie wykrywają błędnego SDK; wiele parametrów zwiększa licznik testów |
| test_adapters.py | tryb bojlera, odrzucone komendy Atlantic, wątek HTTP | prawdziwe odpowiedzi i lifecycle transportu |
| test_backend.py | sygnały, kolejność, walidacja błędów | cache po błędzie i częściowy start |
| test_panel_commands.py | identyfikacja urządzeń, blokady, pralka offline | opóźniony readback i późne zakończenie wątku |
| test_fan_control.py | realne SDK + fake transport nawiewu | refresh SDK i potwierdzenie zasilania |
| test_demo.py | usługi demo bez sieci | demo aktualizuje stan natychmiast |
| demo_smoke.py | pełny start QML w demo i wyjście | zasoby produkcyjnego composition root |
| ui_smoke.py | kliknięcia, formularze, błędy, 3 rozdzielczości | prawdziwy dotyk/GPU oraz optymistyczny cache SDK |

## Uruchamianie

W czystym worktree, Python 3.11 lub 3.12:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt -r requirements-demo.txt
    .venv/bin/python -m pip check
    .venv/bin/python Tests/check_integrity.py
    .venv/bin/python Tests/run_offline.py

Runner najpierw sprawdza ochronę offline, a następnie uruchamia pytest
i obydwa istniejące testy QML w osobnych procesach.
Każdy ma limit 180 sekund; testy QML wykonują się także po porażce pytest.
Końcowy kod jest niezerowy, jeżeli którykolwiek etap zawiedzie. Logi, JUnit
i coverage XML trafiają do ignorowanego katalogu test-results/. Bazowy,
śledzony plik .coverage nie jest nadpisywany przez runner.

Do diagnozy pojedynczego scenariusza:

    .venv/bin/python Tests/run_offline.py --pytest-only Tests/Unit/test_audit_regressions.py

Taki wynik nie zastępuje pełnego zestawu. Zwykłe python -m pytest nie instaluje
ochrony runnera i nie jest zalecaną komendą offline.

## Granice izolacji

- Proces potomny dostaje ograniczony zestaw zmiennych; nie dziedziczy haseł,
  DSN, proxy ani pluginów pytest użytkownika. Cache i konfiguracja XDG są tymczasowe.
- Ochrona instalowana przed collection blokuje gniazda sieciowe Python,
  połączenia/DNS, otwieranie .env/tokenów, podprocesy, import produkcyjnego
  composition root oraz Bleak. Testy BLE muszą wstrzykiwać fake port.
- Socketpair AF_UNIX zostaje dostępny dla pętli asyncio. Próbnik IPv6 urllib3
  jest wyłączony, aby sam import biblioteki nie wykonywał bind.
- Przechwycony przez aplikację wyjątek blokady nadal daje niezerowy wynik.
- To zabezpieczenie przed przypadkowym I/O, nie sandbox dla nieufnego kodu.
  Nie blokuje natywnych wywołań C/Qt. Istniejący QML używa zasobów lokalnych;
  nowe komponenty sieciowe wymagają dodatkowej kontroli i izolacji systemowej.
- Nie uruchamiać produkcyjnego entrypointu, nawet z pozornie testowym .env.
  Config/settings.py szuka konfiguracji także obok interpretera i w katalogu użytkownika.

## Dodane scenariusze wykonywalne

| Test | Co sprawdza | Oczekiwany wynik po naprawie |
| --- | --- | --- |
| test_hh01_failed_readback_does_not_publish_optimistic_power | rzeczywiste SDK, niezależny stan fake urządzenia, błąd refresh, powtórna publikacja Qt | brak emisji HEAT jako potwierdzonego stanu po nieudanym readbacku |
| test_hh02_adapter_refresh_matches_installed_sdk_contract | realna klasa pyairstage i fake odpowiedź chmury | online i OFF odczytane bez TypeError |
| test_hh03_mqtt_thread_persists_exactly_one_reading | callback poza pętlą asyncio do fake repozytorium | dokładnie jeden zapis z właściwymi wartościami |
| test_hh04_weather_maps_successful_fake_http_response | prawdziwy adapter, fake HTTP 200, brak wstrzyknięcia brakującego importu | pomiar i poprawne jednostki |
| test_washer_lifecycle.py | start dwa razy, online → błąd → online, stop podczas oczekiwania | jeden task, świeże dane po powrocie, task zamknięty |
| test_repository_contract.py | parametry SQL, błąd zapisu, brak wyniku, zamknięcie poola | parametry oddzielone od SQL, wyjątek propagowany, zasób zamknięty |

HH-01 sprawdza obecnie sygnał backendu, nie klika rzeczywistego QML. Regresja
łącząca QML z SDK pozostaje obowiązkowym rozszerzeniem przy naprawie. HH-02
wiąże kontrakt z pyairstage 3.2.2; nie jest deklaracją zgodności z wersją na Pi.
Repozytorium używa fake poola; poprawność SQL na PostgreSQL wymaga osobnego
testu na jednorazowej bazie. Test pralki dopuszcza powtórny close; nie dowodzi
pełnego cleanup MQTT, pogody ani DB.

## Macierz dalszego pokrycia i kryteria akceptacji

| ID / obszar | Scenariusze i mechanizm | Kryterium |
| --- | --- | --- |
| HH-01, AC/QML | OFF → klik → pending → zgodny odczyt; niezgodny odczyt; błąd zapisu; timeout; późny readback; drugi pokój | busy znika; brak fałszywego potwierdzenia; brak wpływu na drugi AC |
| HH-02, SDK | dwa urządzenia; poprawny payload; brak urządzenia/pól; utrata i powrót transportu | odczyt właściwego urządzenia i jawny błąd; fake na granicy transportu |
| HH-03, persystencja | rzeczywisty wątek, kolejność wielu pomiarów, błąd repo, zamknięta pętla, shutdown z zapisem | brak cichej utraty/duplikacji, jawny wynik i ograniczona kolejka po ustaleniu polityki |
| HH-04, pogoda | HTTP 200/401/503; timeout; wadliwy JSON; jeden cykl pollingu; błąd repo | mapowanie WMO/jednostek, timestamp UTC, brak zapisu błędnych danych, task zatrzymany |
| HH-05, MQTT | fake client i brak startu prawdziwego wątku; null/lista/tekst/NaN/inf; częściowy payload; poprawna następna wiadomość | callback przeżywa błędną wiadomość, ostatni prawidłowy stan nie zostaje uszkodzony |
| HH-06, reconnect | fake connect odmawia 2 razy, potem działa; sterowany zegar zamiast długiego sleep | backoff, jedna aktywna subskrypcja, brak lawiny prób i zatrzymanie w shutdown |
| HH-07, świeżość | online → HTTP 503 → odzyskanie; pierwszy AC błędny, drugi poprawny | niezależne odświeżenia i jawny stale/offline zgodnie z uzgodnionym kontraktem |
| HH-08, Atlantic | realny klient + fake requests: COMPLETED/FAILED/UNKNOWN/IN_PROGRESS, 401, błędny JSON | UNKNOWN/timeout nie oznacza sukcesu, brak automatycznego ponawiania zapisu |
| HH-09, ustawienia OFF | OFF/HEAT/FAN, błąd każdej kolejnej operacji, anulowanie | zgodność z zaakceptowaną kolejnością; bez niezamierzonego włączenia |
| HH-10, sensory | pusty cache, rzeczywiste zero, częściowe dane, ponowne połączenie | brak danych rozróżniony od zera w DB i QML; kontrakt sygnałów wymaga decyzji |
| HH-11, lifecycle | fake wszystkie zasoby; błąd inicjalizacji po każdym kroku; start/stop dwukrotnie; SIGTERM w izolowanym procesie | brak pozostawionych tasków, wątków i połączeń; anulowanie propagowane |
| HH-12, timeout wątku | threading.Event blokuje komendę; anulowanie asyncio; druga komenda | druga sprzeczna komenda nie rusza przed końcem pierwszej; UI pokazuje niepewność |
| HH-13, testy kontraktowe | rzeczywiste klasy SDK z fałszywym transportem zamiast samych AsyncMock | zmiana API SDK psuje test przed wdrożeniem |
| HH-14, konfiguracja | fikcyjne pliki i ścieżki, priorytet .env, brak kluczy; instalacja na Python 3.11/ARM | brak odczytu produkcyjnych sekretów, powtarzalne zależności |
| Bojler | fake SDK: power/mode/temp, energia, brak pól, opóźnienie, 401/503 | walidacja, jawny błąd, brak fałszywego sukcesu i odzyskanie stanu |
| BLE | fake snapshot/notify, wadliwy payload, zerwanie i powrót, timeout skanu | brak starego odliczania, kontrolowane zamknięcie; bez skanu fizycznego BLE |
| PostgreSQL integracja | jednorazowy lokalny serwer CI, testowy DSN, insert/read/order/close i odrzucenie połączenia | zgodność schematu i parametrów; żadnego DSN z sekretów produkcji |

Testy asynchroniczne powinny synchronizować zdarzenia Event/Queue, zamiast
zgadywać czas za pomocą sleep. Limit oczekiwania służy wykryciu zawieszenia,
nie symulacji opóźnień chmury. W testach wątków zawsze zwalniać Event w finally.

## AUTO-01 — cykliczne odświeżanie urządzeń co 15 minut

Wymaganie dodane na prośbę użytkownika: podczas działania aplikacji automatycznie
pobierać aktualny stan urządzeń co **15 minut (900 sekund)** i przekazywać wynik
do QML bez naciskania „Odśwież”. Jest to zaplanowana funkcja; nie została jeszcze
zaimplementowana. Obecny timer 10-sekundowy publikuje wyłącznie cache i nie
spełnia tego wymagania.

Zakres i kryteria akceptacji:

- Po początkowym odczycie uruchomić jeden harmonogram odczytów co 900 sekund
  dla urządzeń odpytywanych przez API (klimatyzatory, bojler, grzejniki).
  Sensory MQTT i monitor BLE zachowują istniejące mechanizmy aktualizacji;
  cykl nie może tworzyć dodatkowych klientów, subskrypcji ani monitorów.
- Pobierać świeże dane przez adaptery, a następnie aktualizować QML, również
  po zmianach wykonanych pilotem lub inną aplikacją. Odczyt nie wysyła poleceń
  zmiany zasilania, temperatury, trybu ani harmonogramu urządzenia.
- Odczyt potwierdzający polecenie użytkownika (HH-01/HH-02) rozpoczynać po
  poleceniu; nie czekać na 15-minutowy cykl. Przycisk „Odśwież” nadal umożliwia
  odczyt na żądanie.
- Nie nakładać odczytów tego samego urządzenia z cyklu, przycisku i obsługi
  polecenia. Jeżeli poprzedni odczyt nadal trwa, nie dodawać duplikatu do kolejki.
  Nie dopuszczać, aby starszy wynik nadpisał nowsze potwierdzenie polecenia.
- Awaria jednego urządzenia nie blokuje aktualizacji pozostałych. Odczyty mają
  ograniczony czas; błąd nie zmienia starego cache w potwierdzony bieżący stan.
  Następny cykl podejmuje kolejną próbę, bez automatycznego ponawiania komend.
- Aktualizacje działają asynchronicznie i nie blokują panelu. Ponowne
  odświeżenie/inicjalizacja nie tworzy drugiego harmonogramu. Zamknięcie aplikacji
  zatrzymuje harmonogram; po wznowieniu nie wykonuje się lawina zaległych cykli.

Testy z kontrolowanym zegarem i fake transportami, bez oczekiwania 15 minut:

1. Po starcie: brak cyklicznego odczytu przed 900 s; po 900 s jeden cykl;
   po kolejnych 900 s następny. Publikacja cache nie jest liczona jako odczyt.
2. Zmiana stanu fake urządzenia poza HomeHub: najbliższy cykl aktualizuje
   właściwe sygnały Qt i widok QML bez kliknięcia „Odśwież”.
3. Kliknięcie włączenia między cyklami: natychmiastowa ścieżka potwierdzenia
   odczytem; nie czeka do kolejnego terminu harmonogramu.
4. Zbieżność cyklu, przycisku i polecenia; odczyt trwający ponad interwał:
   brak równoległych odczytów tego samego urządzenia i nadpisania nowszego stanu.
5. Timeout/błąd jednego urządzenia oraz późniejszy powrót: pozostałe aktualizują
   się, a odzyskany odczyt wraca do QML w kolejnym cyklu.
6. Start/stop, ponowna inicjalizacja i wznowienie: jeden harmonogram, brak
   osieroconych zadań i dodatkowych subskrypcji; zero wywołań metod sterujących.

Planowany osobny branch: feature/periodic-device-refresh. Realizacja po
ustabilizowaniu odczytów i ich współbieżności (HH-01, HH-02, HH-07, HH-11, HH-12).
Dodanie wymagania do planu nie stanowi rozpoczęcia implementacji fazy 4.

## QML headless

Wykorzystujemy istniejące PySide6.QtTest, QTest, qasync i demo; bez nowego
frameworka. Osobne procesy dla demo_smoke i ui_smoke eliminują konflikt
QCoreApplication/QGuiApplication. Ustawienia: QT_QPA_PLATFORM=offscreen oraz
QT_QUICK_BACKEND=software. ui_smoke obejmuje 1280×720, 800×480, 720×1280,
sygnały pralki, formularze, błąd zapisu i izolację szkiców ustawień.

Rozszerzenie HH-01 musi zasilać ten sam rzeczywisty komponent QML fake backendem
z realnym adapterem/SDK. Osobno sprawdzać checked, busy, failed i wiadomość
po błędzie oraz po ponownym odczycie. Stan fizycznego fake urządzenia musi
być oddzielony od cache SDK. Nie weryfikować wyłącznie liczby wywołań metod.

## Propozycja GitHub Actions

Plik ci-tests.proposed.yml jest poza .github/workflows i nie uruchamia żadnej
automatyzacji. Po zatwierdzeniu scalić kroki z obecnym jobem testowym, zachowując
needs: test i warunek deployu wyłącznie push na main. Nie tworzyć dwóch jobów
o identycznej nazwie w równoległych workflow wymaganych przez ochronę brancha.

Propozycja obejmuje aktualizacje PR, Python 3.11, runner GitHub ubuntu-latest,
pip check, składnię i integralność, pełne testy wraz z jawnymi regresjami,
QML oraz artefakty nawet po porażce. Brak sekretów, self-hosted i deployu.
Obecnie regresje mają blokować merge. Po naprawie dopiero udany run na GitHub
może uzasadniać wymagany status ochrony main. Nie uruchomiono nowego workflow,
nie zmieniono branch protection i nie wykonano pushu.

Nie ustalamy arbitralnego progu coverage. Najpierw wymagamy scenariuszy
behawioralnych; raport procentowy jest wskaźnikiem braków, nie kryterium
poprawności. Zależności pozostałe poza requirements-demo mają zakresy >=;
pełny lock wymaga wersji wspieranych na Pi i jest osobnym zadaniem HH-14.

## Kolejność fazy 4 i punkt zatwierdzenia

1. HH-03 (P0): zapis pomiarów z wątku; osobny fix/mqtt-persistence.
2. HH-02: kontrakt SDK po weryfikacji wersji na Pi; fix/ac-refresh-contract.
3. HH-01: potwierdzenie stanu AC i regresja QML; fix/ac-state-confirmation.
4. HH-04, HH-05, HH-06: pogoda, walidacja MQTT, reconnect — osobne branche.
5. HH-07–HH-12 po uzgodnieniu semantyki stale/offline, OFF i częściowego startu.
6. AUTO-01: cykliczne odświeżanie urządzeń co 15 minut; osobny
   feature/periodic-device-refresh, po spełnieniu zależności opisanych powyżej.

Przed poprawkami potrzebne jest zatwierdzenie listy i tego planu. Dla HH-01
domyślnie testujemy zasilanie raportowane przez urządzenie, nie pracę sprężarki.
Użytkownik zatwierdził zachowanie ostatniego potwierdzonego stanu z widocznym
błędem po nieudanym potwierdzeniu AC. W tej fazie nie zapadła
decyzja o zmianie zachowania HH-09 ani harmonogramów ogrzewania.
