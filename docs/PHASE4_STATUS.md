# Faza 4 — pierwsza partia niezależnych napraw

Wszystkie branche wywodzą się z 2552c9b (1 października 2026) i wspólnego
pakietu testowego audit/test-environment. Praca użytkownika w wcześniejszym
workspace pozostaje bez zmian. Nie wykonywano merge, force push ani deployu.

| Problem | Branch / katalog | Pełny pytest lokalnie | QML |
| --- | --- | --- | --- |
| HH-03, zapis MQTT | fix/mqtt-persistence / HomeHub-fix-mqtt | 205 pass, 3 fail: HH-01/02/04 | startup + UI PASS |
| HH-02, refresh AC | fix/ac-refresh-contract / HomeHub-fix-ac-refresh | 207 pass, 3 fail: HH-01/03/04 | startup + UI PASS |
| HH-01, przełącznik AC | fix/ac-state-confirmation / HomeHub-fix-ac-state | 218 pass, 2 fail: HH-03/04 | startup + UI + realny QML/SDK readback PASS |
| HH-04, pogoda | fix/weather-refresh / HomeHub-fix-weather | 206 pass, 3 fail: HH-01/02/03 | startup + UI PASS |

Są to niezależne branche, a nie jedna scalona wersja. Dlatego każdy nadal
zawiera niepoprawione regresje innych problemów. Nie usuwano testów, nie
stosowano xfail/skip i nie oznaczono tych branchy jako gotowych do produkcji.
HH-01 zależy od HH-02; pozostałe naprawy bazują na wspólnym pakiecie testów.
Wyników nie należy sumować jako liczby unikalnych testów.

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

## Ograniczenia i dalszy zakres

- Pełne lokalne testy wymagają wykonania Qt poza sandboxem ograniczającym NEON.
  W testowym .venv skorygowano flagę hidden pluginów Qt po błędzie offscreen.
- Wersja SDK na Pi pozostaje niepotwierdzona. Nie zmieniono zależności produkcji.
- HH-05–HH-14 i AUTO-01 nie są oznaczone jako naprawione. AUTO-01 ma zaakceptowany
  interwał 15 minut i pozostaje zaplanowany po ustabilizowaniu odczytów/lifecycle.
- HH-09 wymaga decyzji o zachowaniu ustawień na wyłączonym AC; nie zmieniono go.
- Wspólne zamykanie MQTT/DB/pogody i ochrona wątku komendy po anulowaniu
  (HH-11/12) wymagają osobnego projektu i review przed większą zmianą architektury.

Faza 4 jest rozpoczęta, ale nie zakończona. Fazy 5 i 6 nie zostały uruchomione.
