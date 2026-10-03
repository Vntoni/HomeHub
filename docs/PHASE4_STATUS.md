# Faza 4 — stan napraw i Pull Requestów

Wszystkie branche wywodzą się z 2552c9b (1 października 2026) i wspólnego
pakietu testowego audit/test-environment. Praca użytkownika w wcześniejszym
workspace pozostaje bez zmian. Nie wykonywano merge, force push ani deployu.

| Problem | Branch / katalog | Pełny pytest lokalnie | QML |
| --- | --- | --- | --- |
| HH-03, zapis MQTT | fix/mqtt-persistence / HomeHub-fix-mqtt | 205 pass, 3 fail: HH-01/02/04 | startup + UI PASS |
| HH-02, refresh AC | fix/ac-refresh-contract / HomeHub-fix-ac-refresh | 207 pass, 3 fail: HH-01/03/04 | startup + UI PASS |
| HH-01, przełącznik AC | fix/ac-state-confirmation / HomeHub-fix-ac-state | 218 pass, 2 fail: HH-03/04 | startup + UI + realny QML/SDK readback PASS |
| HH-04, pogoda | fix/weather-refresh / HomeHub-fix-weather | 206 pass, 3 fail: HH-01/02/03 | startup + UI PASS |
| HH-05, walidacja MQTT | fix/mqtt-payload-validation / HomeHub-fix-mqtt-validation | 223 pass, 4 fail: HH-01/02/03/04 | startup + UI PASS |
| HH-06, reconnect MQTT | fix/mqtt-reconnect / HomeHub-fix-mqtt-reconnect | 216 pass, 3 fail: HH-01/02/04 | startup + UI PASS |
| HH-08, wynik Atlantic | fix/atlantic-confirmation / HomeHub-fix-atlantic-confirmation | 218 pass, 4 fail: HH-01/02/03/04 | startup + UI PASS |
| HH-09, blokada ustawień OFF | fix/ac-settings-off / HomeHub-fix-ac-state | 227 pass, 2 fail: HH-03/04 | startup + UI + AC readback PASS |
| HH-10, brak pomiaru | fix/sensor-missing-data / HomeHub-fix-mqtt | 223 pass, 3 fail: HH-01/02/04 | startup + mapa temperatur + UI PASS |
| HH-12, cykl życia operacji | fix/operation-lifecycle / HomeHub-fix-operation-lifecycle | 231 pass, 2 fail: HH-03/04 | startup + UI + AC readback PASS |
| HH-07, świeżość danych | fix/device-freshness / HomeHub-fix-device-freshness | 235 pass, 2 fail: HH-03/04 | startup + utrata/powrót odczytu + AC PASS |
| HH-11, zamykanie | fix/application-shutdown / HomeHub-fix-application-shutdown | 246 pass, 2 fail: HH-03/04; później dodany test MQTT: 1 pass | startup/UI PASS; AC/SIGTERM/błąd QML PASS w ponowieniu |
| AUTO-01, odświeżanie | feature/periodic-device-refresh / HomeHub-feature-periodic-refresh | 247 pass, 2 fail: HH-03/04 | 5 smoke PASS, także timer, wolne API i równoległy refresh |

Są to niezależne branche, a nie jedna scalona wersja. Dlatego każdy nadal
zawiera niepoprawione regresje innych problemów. Nie usuwano testów, nie
stosowano xfail/skip i nie oznaczono tych branchy jako gotowych do produkcji.
HH-01 zależy od HH-02, HH-09 od HH-01, a HH-06 i HH-10 od HH-03.
HH-12 bazuje na HH-09, HH-07 na HH-12, HH-11 na HH-07, a AUTO-01 na HH-11.
Pozostałe naprawy bazują na wspólnym pakiecie testów.
Wyników nie należy sumować jako liczby unikalnych testów.

Katalog HomeHub-fix-ac-state jest obecnie na fix/ac-settings-off, a HomeHub-fix-mqtt
na fix/sensor-missing-data. Poprzednie branche HH-01 i HH-03 i ich commity zachowano.

Każda naprawa ma opis przyczyny, odtworzenia, zmian, testów, ryzyka i rollbacku
w swoim docs/HH-XX_CHANGE.md. Logi lokalne: test-results/ w każdym worktree.
Wszystkie testy integracji używały fake transportów; sprzętu nie testowano.

## Strategia PR

Pakiet testowy ma draft PR do main, a niezależne naprawy draft PR do
audit/test-environment. HH-01 ma bazę fix/ac-refresh-contract. Dzięki temu
review każdej naprawy pokazuje wyłącznie jej zakres. Bez samodzielnego scalania.
Pakiet testowy sam ma czerwone regresje i nie jest przeznaczony do wdrożenia.
Po review potrzebna będzie uzgodniona integracja zatwierdzonych zmian i pełny
zielony run całego zestawu przed zmianą main.

Obecny workflow reaguje na PR do main, nie na PR do audit/... lub fix/....
Nie deklarujemy więc checków GitHub Actions dla branchy napraw. Ich wyniki
są lokalne. Propozycja CI z fazy 3 pozostaje poza aktywnym katalogiem workflow;
ustawienia ochrony repozytorium pozostają bez zmian.

Draft PR-y (bez merge):

- [#1 — baza testowa](https://github.com/Vntoni/HomeHub/pull/1)
- [#2 — HH-03](https://github.com/Vntoni/HomeHub/pull/2)
- [#3 — HH-02](https://github.com/Vntoni/HomeHub/pull/3)
- [#4 — HH-01](https://github.com/Vntoni/HomeHub/pull/4)
- [#5 — HH-04](https://github.com/Vntoni/HomeHub/pull/5)
- [#6 — HH-05](https://github.com/Vntoni/HomeHub/pull/6)
- [#7 — HH-06](https://github.com/Vntoni/HomeHub/pull/7)
- [#8 — HH-09](https://github.com/Vntoni/HomeHub/pull/8)
- [#9 — HH-10](https://github.com/Vntoni/HomeHub/pull/9)
- [#10 — HH-08](https://github.com/Vntoni/HomeHub/pull/10)
- [#11 — HH-12](https://github.com/Vntoni/HomeHub/pull/11)
- [#12 — HH-07](https://github.com/Vntoni/HomeHub/pull/12)
- [#13 — HH-11](https://github.com/Vntoni/HomeHub/pull/13)
- [#14 — AUTO-01](https://github.com/Vntoni/HomeHub/pull/14)

[CI bazy testowej, commit ebaa7cf](https://github.com/Vntoni/HomeHub/actions/runs/37062652609)
na Linux/Python 3.11.16 potwierdziło 199 pass, 4 fail (HH-01–04), jedno ostrzeżenie
SDK. Job wdrożenia został SKIPPED. Test interakcji QML tego workflow został także
SKIPPED po błędzie pytest — wyniki QML w tabeli pochodzą z lokalnego runnera, który
wykonuje je mimo błędów pytest. Nie ustanawiano wymaganych checków ochrony main.

## Uzupełnienia ostatnich poprawek

- Kontynuacja 3 października: poprzednie deklaracje domknięcia HH-07/11 były
  przedwczesne. Trzy nowe testy HH-07 odtworzyły utratę spójnego snapshotu i
  uznawanie pustej odpowiedzi Atlantic za sukces; po poprawce przechodzą.
- HH-11: odtworzono przerwanie cleanup po błędzie jednego zasobu. Poprawiono
  kolejność sensor → DB, preferowanie `aclose()`, scope zasobów przy błędzie
  startu, SIGTERM i cleanup po błędzie QML. Guard blokujący produkcyjną
  kompozycję pozostał aktywny; scope startupu jest testowany na fake zasobach.
- AUTO-01: test QML wykonuje realny timer ze skróconym testowym interwałem,
  sprawdza odczyt zmiany, brak równoległych cykli i brak setterów. Produkcyjny
  interwał to 900000 ms. Backend współdzieli cykl timer/ręczne odświeżenie.
- Wcześniejszy problem DNS występował w sandboxie; odczyt i push poza nim
  działają. Nie potwierdzono tezy, że modele mają osobne połączenia z GitHub.
- HH-09: samo sprawdzenie cache nie wystarczało. Nowa regresja wykazała 6 fail,
  1 pass; dodatkowy odczyt przed setterami blokuje OFF/nieznany tryb/błąd chmury.
- HH-10: sygnał `object` dawał błędy PyObjectWrapper w istniejącej mapie temperatur.
  Zmieniono go na QVariant; test rzeczywistego QML sprawdza brak → zero → pomiar.
- Wcześniejsze komunikaty o braku widoku sensorów były nieprawidłowe: odbiorcą
  sygnałów jest TemperatureMap.qml. Dokument HH-10_CHANGE został skorygowany.

## Ograniczenia i dalszy zakres

- Pełne lokalne testy wymagają wykonania Qt poza sandboxem ograniczającym NEON.
  W testowym .venv skorygowano flagę hidden pluginów Qt po błędzie offscreen.
- Wersja SDK na Pi pozostaje niepotwierdzona. Nie zmieniono zależności produkcji.
- HH-07, HH-11, HH-12 i AUTO-01 są opublikowane jako draft PR-y. Nie są gotowe
  do wdrożenia bez review oraz wspólnego zielonego przebiegu po integracji
  niezależnych napraw. Szczególnie HH-11 wymaga wspólnej weryfikacji końcowych
  zapisów MQTT z HH-03/06. Nie scalano PR-ów.
- HH-09 i HH-10 mają zatwierdzone zachowanie i przetestowane poprawki powyżej.
- Użytkownik zatwierdził zachowanie ostatnich danych z oznaczeniem nieaktualności
  po błędzie bojlera/grzejników (HH-07).
- Aktualne HEAD-y: HH-12 `8c4d7f7`, HH-07 `958526b`, HH-11 `8cdd272`,
  AUTO-01 `818ea4b`. Omyłkowy timer usunięto z zakresu HH-11 jawnym revertem.
  Lokalną historię nieopublikowanych jeszcze HH-11/AUTO-01 uporządkowano,
  zachowując oryginały jako `fix/application-shutdown-initial` i
  `feature/periodic-device-refresh-initial`. Bez force push i utraty commitów.
- HH-13: testy kontraktów rozłożone są na PR-y napraw, ale wspólne CI nadal
  wymaga integracji. HH-14: wersje SDK z Pi i finalne constraints pozostają
  niezweryfikowane; nie zmieniano zależności produkcyjnych na podstawie macOS.
- Wybór wariantu architektury dla HH-07/11/12 i AUTO-01 opisuje
  [REFRESH_LIFECYCLE_PROPOSAL.md](REFRESH_LIFECYCLE_PROPOSAL.md). Wariant A jest
  zatwierdzony przez użytkownika w bieżącej rozmowie; implementacja w kolejnych
  osobnych branchach, bez automatycznego scalania PR-ów.

Faza 4 jest rozpoczęta, ale nie zakończona. Fazy 5 i 6 nie zostały uruchomione.
