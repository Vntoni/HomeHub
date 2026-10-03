# HomeHub — audyt funkcjonalny i stabilności, faza 1

Data audytu: 2026-10-02
Audytowana wersja: **`2552c9b51cc77604af3e3e3c861ad3bd11e5009b`** — `Enlarge device icons for the Raspberry Pi touch panel`, commit z 1 października 2026.

Raport dotyczy wyłącznie tego commita. Kod tego commita został pobrany do izolowanej kopii roboczej w `/tmp/homehub-audit-remote`; nie wykonano checkoutu, merge, rebase, push ani wdrożenia na urządzenia.

## Stan audytu

Audyt fazy 1 jest zakończony. Nie zmieniałem kodu aplikacji, konfiguracji produkcyjnej ani ustawień GitHub. Raport zapisano na lokalnym branchu `audit/stabilization`; dalsze naprawy wymagają osobnej akceptacji.

Wszystkie testy urządzeń i transportów wykonane podczas audytu korzystały z mocków, symulatorów lub fałszywego transportu. Nie sterowałem prawdziwą klimatyzacją, bojlerem, grzejnikami ani pralką.

## Zgłoszony problem: przełącznik zasilania klimatyzacji

### Objaw

Po kliknięciu włączenia klimatyzacji przełącznik zmieniał stan niezależnie od tego, czy urządzenie faktycznie przyjęło i wykonało polecenie. Użytkownik nie widział późniejszego, wiarygodnego potwierdzenia stanu urządzenia.

### Wynik audytu

Problem został odtworzony w badanym commicie jako **HH-01, P1**. Nie jest to wyłącznie problem wizualny przycisku.

Ścieżka działania:

1. `DeviceCard.qml` wysyła `powerRequested(checked)` i wiąże stan przełącznika z `powered`.
2. `Accontrol.qml` wywołuje `backend.apply_device_power("ac", room, on)` i ustawia `busy`.
3. Biblioteka `pyairstage` optymistycznie aktualizuje własny cache po przyjęciu zapisu.
4. Backend wykonuje `refresh()` i później publikuje dashboard.
5. Jeżeli odświeżenie zakończy się błędem, `finally` nadal wywołuje `publish_dashboard()`.
6. `publish_dashboard()` odczytuje cache biblioteki, więc QML może dostać żądany stan zamiast ostatniego potwierdzonego stanu urządzenia.

Kontrolowane odtworzenie z rzeczywistym QML i klasą SDK, ale fałszywym transportem, dało taki rezultat:

| Etap | Przełącznik | `busy` | `failed` | Niezależny stan symulowanego urządzenia |
|---|---:|---:|---:|---:|
| Przed kliknięciem | OFF | false | false | OFF |
| Polecenie w toku | OFF | true | false | OFF |
| Po błędzie odświeżenia | **ON** | false | true | **OFF** |
| Następna publikacja dashboardu | **ON** | false | true | **OFF** |

Potwierdzona przyczyna techniczna: UI nie rozróżnia ostatniego potwierdzonego odczytu, oczekującego polecenia i stanu niepotwierdzonego, a backend publikuje cache także po nieudanym odświeżeniu. Timer dashboardu publikuje cache i sam nie wykonuje ponownego odczytu z chmury.

Oczekiwane zachowanie do utrwalenia testem: przełącznik może pokazywać stan oczekiwania podczas wysyłania, ale po błędzie lub braku zgodnego readbacku nie może przedstawiać żądanego stanu jako potwierdzonego stanu urządzenia.

Odczyt `ON` oznacza stan zasilania raportowany przez urządzenie. Nie musi oznaczać, że sprężarka w tej chwili aktywnie grzeje lub chłodzi.

## Architektura badanego commita

`View/main.py` tworzy `QGuiApplication`, pętlę `qasync.QEventLoop`, composition root i `QtHomeBackend`. QML otrzymuje backend przez context property. `backend.init_all()` jest uruchamiane jako zadanie asyncio.

```text
QML
  -> QtHomeBackend / asyncSlot
  -> serwisy App
  -> porty Ports i adaptery Adapters
  -> biblioteki dostawców oraz transporty
  <- cache i readback
  <- sygnały Qt
  <- właściwości QML
```

Integracje:

| Obszar | Implementacja | Istotne cechy |
|---|---|---|
| Klimatyzacja | `ClimateService` → `AirstageACAdapter` → `pyairstage` | Sterowanie zasilaniem, trybem, temperaturą i nawiewem; cache SDK |
| Bojler | `WaterHeaterService` → `AristonBoilerAdapter` → `ariston` | Odświeżanie stanu i energii |
| Grzejniki | `HeaterService` → `CozyTouchHeaterAdapter` → `atlantic_client.py` | Synchroniczne HTTP uruchamiane przez `asyncio.to_thread` |
| Pralka | `WasherService` → `WasherBleAdapter` → Bleak | Skan BLE, notify i zapisy inicjalizujące GATT |
| Sensory | `ZigbeeSensorAdapter` → Paho MQTT | Osobny wątek daemon i osobny klient dla sensora |
| Persystencja | `PostgresRepositoryAdapter` → asyncpg | Pool połączeń, tworzenie tabel przy starcie |
| Pogoda | `OpenMeteoAdapter` | Dwie definicje klasy w jednym pliku; druga przesłania pierwszą |

Asynchroniczność jest mieszana: Qt i asyncio działają na wspólnej pętli, część HTTP jest synchroniczna, MQTT działa w osobnych wątkach, a zapisy do PostgreSQL są planowane jako taski asyncio. `apply_*` mają blokady per urządzenie, walidację i timeout 45 sekund, ale nie gwarantują jeszcze zgodności readbacku z żądaniem.

## Testy bazowe

Dla `2552c9b` uruchomiono istniejące testy przed jakimikolwiek naprawami:

| Sprawdzenie | Wynik |
|---|---|
| `pytest Tests/` | **196 passed in 3.70s** |
| Coverage `App`, `Adapters`, `Ports`, `Interface` | **56%**; 864 statements, 378 niepokrytych |
| `Tests/ui_smoke.py` | **PASS**; karty, formularze, zapis ustawień, błędy zapisu, przełączniki, nawiew i status pralki |
| Rozmiary UI | 1280×720, 800×480, 720×1280 |
| Diagnostyka HH-01 | **Odtworzona**; prawdziwy komponent QML i klasa SDK, fałszywy transport, sieć zablokowana |

Test UI zakończył się bez ostrzeżeń QML. Nie zastępuje to testu dotyku, GPU, sieci ani sprzętu na Raspberry Pi.

Luki w coverage:

| Obszar | Coverage | Luka |
|---|---:|---|
| Adapter AC | 66% | Brak testu zgodności refresh z SDK i wiarygodnego readbacku zasilania |
| Adapter Ariston | 62% | Brak testów rzeczywistych odpowiedzi SDK, opóźnień i błędów energii |
| Adapter Atlantic | 50% | Brak pełnego pokrycia klienta, statusów operacji i współbieżności |
| MQTT, PostgreSQL, pogoda, BLE | 0% | Brak testów transportu, zapisu, reconnectu i walidacji danych |
| `WasherService` | 19% | Brak pełnego lifecycle i testów powrotu po rozłączeniu |
| Backend Qt | 79% | Brak części scenariuszy błędów startu, cache i anulowania |

Istniejąca zielona suite nie wykrywa HH-01, ponieważ demo przechowuje stan bez opóźnień i bez optymistycznego cache prawdziwego SDK.

## Raport problemów

Oznaczenia dowodów: **O** — odtworzone kontrolowanym testem, **S** — potwierdzone w kodzie, **H** — podejrzenie wymagające sprawdzenia integracyjnego.

### HH-01 — przełącznik AC pokazuje żądany stan bez potwierdzenia

- **Priorytet:** P1.
- **Status:** Odtworzone w `2552c9b`; odpowiada zgłoszeniu użytkownika.
- **Pliki/funkcje:** `View/Example/Components/DeviceCard.qml:onToggled`, `Accontrol.qml:onPowerRequested/onModeReceived`, `Interface/qt_backend.py:apply_device_power/publish_dashboard`, `Adapters/airstage_ac_adapter.py`, `pyairstage.AirstageAC`.
- **Odtworzenie:** użyć cache AC w stanie OFF, fałszywego transportu przyjmującego zapis oraz niezależnego symulowanego urządzenia pozostającego OFF; kliknąć przełącznik QML; wymusić błąd refresh; wykonać kolejne `publish_dashboard()`.
- **Zaobserwowany rezultat:** backend zgłasza błąd, ale przełącznik i `powered` pozostają ON, mimo że urządzenie symulowane jest OFF.
- **Oczekiwany rezultat:** ON jest pokazywane dopiero po zgodnym, świeżym odczycie albo jako wyraźnie oznaczone oczekiwanie; po błędzie stan wraca do ostatniego potwierdzonego stanu lub do „nieznany”.
- **Przyczyna:** optymistyczny cache SDK plus publikowanie cache po błędzie; brak modelu potwierdzonego readbacku.
- **Proponowana naprawa:** oddzielić stan potwierdzony od oczekującego, wykonać ograniczony readback, porównać go z żądaniem i zachować wynik „niepotwierdzone” po timeoutach/odrzuceniu. Nie ponawiać automatycznie nieidempotentnego polecenia.
- **Ryzyko regresji:** opóźniona chmura, równoczesna zmiana z innego panelu, polecenie wykonane mimo timeoutu.
- **Test regresyjny:** zgodny readback, niezgodny readback, błąd refresh po zapisie, odrzucenie zapisu, timeout, późniejsze odzyskanie i izolacja drugiego AC. Jeden test musi używać prawdziwej klasy SDK z fake transportem i rzeczywistego QML.

### HH-02 — refresh AC jest niezgodny z `pyairstage 3.2.2`

- **Priorytet:** P1.
- **Status:** Odtworzone w środowisku audytu; wersja biblioteki na Raspberry Pi nie została zweryfikowana.
- **Pliki/funkcje:** `Adapters/airstage_ac_adapter.py:refresh`, `pyairstage.AirstageAC.refresh_parameters`.
- **Odtworzenie:** utworzyć adapter z prawdziwą klasą `AirstageAC` i fake `ApiCloud.get_devices`, następnie wykonać `await adapter.refresh()`.
- **Zaobserwowany rezultat:** `TypeError: isinstance() arg 2 must be a type...`; SDK ma synchroniczne `refresh_parameters(data=...)`, a adapter traktuje je jak coroutine.
- **Oczekiwany rezultat:** poprawne pobranie danych, aktualizacja cache i statusu online.
- **Przyczyna:** niedopasowanie adaptera do badanego kontraktu SDK; istniejące mocki zakładają inny interfejs.
- **Proponowana naprawa:** potwierdzić wersję SDK na Pi, przygotować test kontraktowy z fake transportem i dopiero potem dostosować adapter.
- **Ryzyko regresji:** różne formaty odpowiedzi, wersje biblioteki i identyfikatory urządzeń.
- **Test regresyjny:** dwa urządzenia, poprawny payload, brakujące pola, timeout i ponowne połączenie.

### HH-03 — cicha utrata zapisów MQTT

- **Priorytet:** P0 — problem może powodować cichą utratę historii pomiarów.
- **Status:** Odtworzone kontrolowanym testem wątku.
- **Pliki/funkcje:** `App/sensor_service.py:record_reading`, callback w `Compositions/compositions.py`.
- **Odtworzenie:** wywołać `record_reading()` z pomocniczego `threading.Thread` przy fake repozytorium.
- **Zaobserwowany rezultat:** `asyncio.get_event_loop()` w wątku rzuca `RuntimeError`, a wyjątek jest pomijany; zapis nie następuje.
- **Oczekiwany rezultat:** dokładnie jeden zapis albo jawny sygnał błędu/buforowania.
- **Przyczyna:** brak bezpiecznego handoffu do pętli asyncio i `except RuntimeError: pass`.
- **Proponowana naprawa:** przekazać referencję do pętli, użyć kontrolowanego handoffu między wątkiem a asyncio oraz obsłużyć zamkniętą pętlę.
- **Ryzyko regresji:** kolejność pomiarów, obciążenie bazy, shutdown i rozmiar kolejki.
- **Test regresyjny:** wątek MQTT, fake repozytorium, błąd repozytorium, zamknięta pętla i zapewnienie braku duplikatów.

### HH-04 — pogoda nie działa przez przesłoniętą klasę

- **Priorytet:** P1.
- **Status:** Odtworzone bez sieci.
- **Pliki/funkcje:** `Adapters/open_meteo_adapter.py`, obie definicje `OpenMeteoAdapter`.
- **Odtworzenie:** wywołać `await OpenMeteoAdapter(0, 0).fetch()`.
- **Zaobserwowany rezultat:** `name 'httpx' is not defined`, wynik `None`.
- **Oczekiwany rezultat:** fake odpowiedź HTTP powinna zostać zmapowana i zapisana albo jawnie oznaczona jako niedostępna.
- **Przyczyna:** druga definicja klasy przesłania pierwszą, a aktywna implementacja odwołuje się do niezaimportowanego `httpx`.
- **Proponowana naprawa:** pozostawić jedną implementację i jeden jawny klient HTTP.
- **Ryzyko regresji:** timeouty, mapowanie kodów WMO, jednostki wiatru i zapis timestampu.
- **Test regresyjny:** poprawna odpowiedź, błąd HTTP, niepełny JSON i jeden cykl zapisu do fake repozytorium.

### HH-05 — błędny payload MQTT może przerwać callback

- **Priorytet:** P1.
- **Status:** Odtworzone na fake adapterze.
- **Pliki/funkcje:** `Adapters/zigbee_sensor_adapter.py:_on_message`, `App/sensor_service.py`.
- **Odtworzenie:** wysłać payloady `[]`, `{"temperature": null}` i `{"temperature": "oops"}`.
- **Zaobserwowany rezultat:** odpowiednio `AttributeError`, `TypeError` i `ValueError` wychodzą z callbacku.
- **Oczekiwany rezultat:** błędny pomiar zostaje odrzucony lub oznaczony, a następna poprawna wiadomość nadal jest obsługiwana.
- **Przyczyna:** obsługiwany jest tylko `JSONDecodeError`; brak walidacji typu, zakresu i wartości skończonych.
- **Proponowana naprawa:** walidować strukturę i liczby przed podmianą cache; wprowadzić status jakości/stale.
- **Ryzyko regresji:** częściowe payloady i różne zakresy sensorów.
- **Test regresyjny:** błędne JSON-y, brak pól, `NaN`, `inf`, poprawny pomiar po błędnym payloadzie.

### HH-06 — brak reconnectu MQTT po awarii początkowej

- **Priorytet:** P1.
- **Status:** Odtworzone na fake kliencie.
- **Pliki/funkcje:** `Adapters/zigbee_sensor_adapter.py:_run`.
- **Odtworzenie:** ustawić `connect.side_effect = ConnectionRefusedError` i uruchomić `_run()`.
- **Zaobserwowany rezultat:** jedno połączenie, zero wejść do `loop_forever`, wątek kończy się wyjątkiem.
- **Oczekiwany rezultat:** jawny offline i kontrolowane ponowienie po uruchomieniu brokera.
- **Przyczyna:** brak retry/backoff i obsługi wyjątku przed pętlą MQTT.
- **Proponowana naprawa:** lifecycle klienta z ograniczonym backoffem, sygnałem stanu i kontrolowanym zatrzymaniem.
- **Ryzyko regresji:** duplikacja wątków/subskrypcji i zbyt częste próby.
- **Test regresyjny:** broker odmawia dwa razy, potem działa; jedna subskrypcja i poprawny powrót danych.

### HH-07 — błąd odczytu pozostawia stary status online

- **Priorytet:** P1.
- **Status:** Odtworzone na fake odpowiedzi HTTP.
- **Pliki/funkcje:** `atlantic_client.py:get_devices`, `CozyTouchHeaterAdapter.refresh/is_online`, `ClimateService.refresh_all`.
- **Odtworzenie:** klient Atlantic ma stare capabilities, a `get_devices()` zwraca HTTP 503; osobno pierwszy z dwóch adapterów AC rzuca błąd refresh.
- **Zaobserwowany rezultat:** grzejnik nadal może być raportowany jako online na podstawie starego cache, a drugi AC nie zostaje odświeżony.
- **Oczekiwany rezultat:** rozróżnienie aktualnego odczytu, starego cache i błędu; niezależne urządzenia powinny być sprawdzane osobno.
- **Przyczyna:** `get_devices()` zwraca pustą listę bez unieważnienia `self.devices`; refresh serwisów jest sekwencyjny.
- **Proponowana naprawa:** przechowywać czas ostatniego poprawnego odczytu, propagować błąd i izolować odświeżanie urządzeń.
- **Ryzyko regresji:** chwilowa niedostępność sieci i semantyka statusu offline/stale.
- **Test regresyjny:** online → błąd → odzyskanie oraz błąd pierwszego AC przy poprawnym drugim AC.

### HH-08 — nieznany status operacji Atlantic jest uznawany za sukces

- **Priorytet:** P1.
- **Status:** Odtworzone z fake odpowiedzi.
- **Pliki/funkcje:** `atlantic_client.py:set_capability`.
- **Odtworzenie:** POST zwraca ID operacji, a 20 kolejnych GET zwraca `state="UNKNOWN"`.
- **Zaobserwowany rezultat:** metoda zwraca `True` po logu „assuming success”.
- **Oczekiwany rezultat:** wynik powinien być niepotwierdzony lub błędny, bez komunikatu o sukcesie urządzenia.
- **Przyczyna:** kod jawnie traktuje ostatni nieznany status jako sukces.
- **Proponowana naprawa:** potwierdzać wyłącznie rozpoznane stany zakończenia i rozdzielić „przyjęto polecenie” od „wykonano”.
- **Ryzyko regresji:** nowe, prawidłowe stany API wymagające późniejszej obsługi.
- **Test regresyjny:** `COMPLETED`, `FAILED`, `IN_PROGRESS`, `UNKNOWN`, timeout, 401 i niepoprawny JSON.

### HH-09 — ustawienia AC z wyłączonego urządzenia mogą zakończyć się błędem przed włączeniem

- **Priorytet:** P1.
- **Status:** Odtworzone z realną klasą SDK i fake transportem; bez sprzętu.
- **Pliki/funkcje:** `QtHomeBackend.apply_ac_settings`, `ClimateService.set_target_temp`, `AirstageAC.set_target_temperature`.
- **Odtworzenie:** cache `ONOFF_MODE=0`, tryb HEAT, następnie zastosowanie temperatury i trybu.
- **Zaobserwowany rezultat:** biblioteka zgłasza `AirstageACError` o braku możliwości ustawienia temperatury w trybie OFF/FAN; włączenie jest planowane dopiero po ustawieniu temperatury.
- **Oczekiwany rezultat:** scenariusz „wyłączone AC → zastosuj ustawienia” ma mieć jednoznaczną, zaakceptowaną kolejność i wynik.
- **Przyczyna:** walidacja temperatury SDK zależy od stanu zasilania, a backend włącza urządzenie dopiero na końcu.
- **Proponowana naprawa:** najpierw ustalić oczekiwaną semantykę i bezpieczną kolejność; nie zmieniać jej automatycznie.
- **Ryzyko regresji:** niezamierzone uruchomienie urządzenia po częściowym błędzie.
- **Test regresyjny:** OFF/HEAT/FAN, każda kolejność zapisów, błąd pośredni i anulowanie.

### HH-10 — brak danych sensora jest prezentowany jako zero

- **Priorytet:** P2.
- **Status:** Potwierdzone w kodzie i odczycie pustego cache.
- **Pliki/funkcje:** `ZigbeeSensorAdapter.get_temperature/get_humidity`, callback composition.
- **Zaobserwowany rezultat:** pusty cache daje `0.0°C` i `0.0%` zamiast braku danych.
- **Oczekiwany rezultat:** brak danych, dane stare i rzeczywiste zero powinny być rozróżnialne.
- **Przyczyna:** `.get(..., 0.0)` bez timestampu i statusu świeżości.
- **Proponowana naprawa:** jawny stan unavailable/stale oraz walidacja przed zapisem.
- **Ryzyko regresji:** sygnały Qt mają typ `float`, a tabele DB wymagają wartości NOT NULL.
- **Test regresyjny:** pusty cache, częściowy payload, rzeczywiste zero i powrót po utracie łączności.

### HH-11 — zasoby i anulowanie nie mają pełnego lifecycle

- **Priorytet:** P2.
- **Status:** Potwierdzone w kodzie; pełnego zamknięcia integracji nie uruchamiano.
- **Pliki/funkcje:** `QtHomeBackend.init_all/shutdown`, `View/main.py`, composition root, repozytorium PostgreSQL i klient MQTT.
- **Zaobserwowany rezultat:** `shutdown()` obsługuje serwis pralki, ale zadanie pogody, pool DB i MQTT nie mają wspólnego właściciela cleanup. Bare `except` może również ukryć anulowanie refreshu.
- **Oczekiwany rezultat:** kontrolowane zatrzymanie wszystkich tasków, wątków i połączeń.
- **Proponowana naprawa:** mały kontrakt lifecycle, referencje do tasków oraz cleanup także po częściowym starcie.
- **Ryzyko regresji:** kolejność zamykania pętli Qt, aktywne requesty i oczekujące zapisy.
- **Test regresyjny:** start/stop, błąd połowy inicjalizacji, anulowanie i brak pozostawionych tasków.

### HH-12 — anulowanie `to_thread` nie zatrzymuje synchronicznej komendy

- **Priorytet:** P2.
- **Status:** Odtworzone na fake komendzie.
- **Pliki/funkcje:** `CozyTouchHeaterAdapter._command`, `QtHomeBackend.apply_heater_settings/apply_device_power`.
- **Odtworzenie:** synchroniczna komenda czeka na `threading.Event`; anulować task asyncio po rozpoczęciu, a następnie uruchomić drugą komendę.
- **Zaobserwowany rezultat:** druga komenda może rozpocząć się przed zakończeniem pierwszej funkcji w wątku.
- **Oczekiwany rezultat:** UI powinno znać stan „komenda nadal trwa” i nie wysyłać sprzecznego następnego polecenia.
- **Proponowana naprawa:** śledzić zakończenie wątku i modelować stan niepotwierdzonej komendy; nie ponawiać automatycznie zapisu.
- **Ryzyko regresji:** responsywność, kolejka urządzenia i zamykanie aplikacji.
- **Test regresyjny:** timeout, druga komenda, kolejność zdarzeń i komunikat wyniku.

### HH-13 — testy nie chronią kontraktów integracyjnych

- **Priorytet:** P3.
- **Status:** Potwierdzone coverage i analizą testów.
- **Pliki/funkcje:** `Tests/Unit/*`, `Tests/ui_smoke.py`, `pytest.ini`, `.github/workflows/ci-cd.yml`.
- **Odtworzenie:** uruchomić pełną suite z coverage i porównać zakres wykonania z adapterami transportów.
- **Zaobserwowany rezultat:** 196 testów przechodzi, mimo że ścieżki MQTT, PostgreSQL, pogody i części adapterów mają 0% coverage; mocki nie wykrywają niezgodności API SDK.
- **Oczekiwany rezultat:** testy powinny wykrywać błędny kontrakt adaptera, utratę zapisu, brak reconnectu i niepotwierdzony stan UI.
- **Przyczyna:** testy skupiają się na delegowaniu metod i usługach demo; brakuje kontraktów transportów oraz testów readbacku.
- **Proponowana naprawa:** dodać testy kontraktowe z realnymi klasami SDK i fake transportem, testy wątków, lifecycle i readbacku. Nie zastępować ich samym zwiększeniem procentu coverage.
- **Ryzyko regresji:** testy mogą ujawnić istniejące błędy CI; nie należy ich wyciszać.
- **Test regresyjny:** zestaw HH-01–HH-12 w izolacji, bez credentiali i sprzętu.

### HH-14 — zależności i dokumentacja konfiguracji są niejednoznaczne

- **Priorytet:** P3.
- **Status:** Potwierdzone w plikach commita.
- **Pliki/funkcje:** `requirements.txt`, `requirements-demo.txt`, `Config/settings.py`, `.env.example`, `Config/.env.example`, `README.md`, `build_app.py`.
- **Odtworzenie:** porównać importy z deklarowanymi zależnościami, klucze `Settings` z przykładami `.env` oraz instrukcję README z rzeczywistym entrypointem.
- **Zaobserwowany rezultat:** `requirements.txt` zawiera głównie zakresy `>=`, README zawiera nieaktualne opisy, a przykłady `.env` nie dokumentują wszystkich ustawień DB, pogody i sensorów.
- **Oczekiwany rezultat:** wspierane środowisko, zależności i konfiguracja powinny być jednoznaczne i odtwarzalne.
- **Przyczyna:** dokumentacja i konfiguracja rozwijały się razem z integracjami bez jednego kontraktu wersji/runtime.
- **Proponowana naprawa:** najpierw odczyt wersji na Pi, potem constraints/lock i korekta dokumentacji; bez hurtowej aktualizacji bibliotek.
- **Ryzyko regresji:** różnice API bibliotek ARM i zachowanie PyInstaller.
- **Test regresyjny:** odtwarzalna instalacja, importy, build smoke oraz test wyboru `.env` z fikcyjnymi ścieżkami.

## Kwestie wymagające decyzji użytkownika

Nie klasyfikuję poniższych punktów jako potwierdzonych błędów funkcjonalnych bez ustalenia zamierzonego zachowania:

- Czy panel ma działać częściowo, gdy chmura AC albo bojlera jest niedostępna podczas startu?
- Jak długo stan z cache może być uznawany za świeży, gdy użytkownik nie naciska „Odśwież”?
- Czy przełącznik AC ma oznaczać zasilanie urządzenia, czy aktywną pracę sprężarki?
- Czy „wyłącz grzejnik” ma anulować nadpisanie temperatury i wznowić harmonogram, czy fizycznie wyłączyć ogrzewanie?
- Jak rozróżniać pralkę wyłączoną, offline, nieaktywną i zakończoną?

## CI/CD i ograniczenia weryfikacji

Ostatni sprawdzony workflow dla `2552c9b` zakończył sukcesem `Run pytest` oraz `Build & Deploy on RPi5`: [run 36928912459](https://github.com/Vntoni/HomeHub/actions/runs/36928912459). Deploy ma warunek `github.ref == 'refs/heads/main' && github.event_name == 'push'`, więc PR i zwykły push feature brancha nie uruchamiają produkcyjnego deployu w tym workflow.

Workflow posiada test UI, concurrency dla wdrożeń, obsługę user systemd/D-Bus, zachowanie `.env` i sprawdzenie usługi po starcie. Nadal nie ma procedury rollbacku. Nie zmieniano branch protection, wymaganych statusów, sekretów, runnera ani środowisk GitHub.

Nie zweryfikowano na Raspberry Pi: wersji Python/SDK/Qt, aktualnej konfiguracji systemd, fizycznych urządzeń, GPU i dotyku, długotrwałej stabilności, reconnectu Wi-Fi/MQTT/BLE, testu zaniku zasilania, rollbacku i odtworzenia bazy. Nie wykonano żadnego sterowania sprzętem.

## Proponowana kolejność dalszych prac po akceptacji

1. Przygotować branch roboczy dokładnie od `2552c9b`.
2. Dodać test regresyjny HH-01 z QML, realną klasą SDK i fake transportem.
3. Naprawić i zweryfikować kontrakt refresh AC (HH-02), a następnie readback przełącznika (HH-01).
4. Osobnymi branchami objąć persystencję MQTT, pogodę, walidację payloadów, reconnect i statusy niepotwierdzone.
5. Dopiero po testach przygotować workflow Git, ochronę `main`, procedurę testów na Pi i rollback.
6. Po stabilizacji przygotować rekomendacje dla ReSpeaker Lite i przyszłego AI; AI nie jest objęte tą fazą.

## Punkt zatrzymania

Raport fazy 1 jest gotowy do zatwierdzenia. Zawiera zgłoszony przez użytkownika problem przełącznika AC, jego odtworzenie, przyczynę, ryzyko i plan testu regresyjnego.

Nie rozpocząłem napraw, nie zmieniłem produkcyjnej konfiguracji, nie wykonałem merge ani wdrożenia. Po akceptacji raportu przejdę wyłącznie do fazy 2.
