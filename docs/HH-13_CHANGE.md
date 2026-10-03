# HH-13 — wspólne testy kontraktów w CI

Workflow testuje każdy PR, także do gałęzi audit/fix. Uruchamia istniejący
runner offline: unit/regresje, startup QML i testy interakcji. Na gałęziach
z HH-11 obejmuje także osobne procesy SIGTERM oraz błędu ładowania QML.
Runner wykonuje smoke testy także po błędzie pytest i nie maskuje błędów.

Instalacja testowa używa istniejących requirements.txt i requirements-demo.txt
(przypięte Qt/qasync/pyairstage). Dochodzą pip check, kontrola integralności,
limit 15 minut oraz logi jako artefakt również przy błędzie.

Deploy zachowuje warunek: wyłącznie push do main po udanym teście. PR-y i
gałęzie eksperymentalne nie wdrażają aplikacji. Nie zmieniono ochrony gałęzi,
nie instalowano runnera na Pi i nie uruchamiano urządzeń.

Regresje HH-01–12 znajdują się na osobnych gałęziach napraw. Ten PR bazuje na
pakiecie testowym i sam ma jego znane cztery czerwone regresje. Zbiorczy wynik
wszystkich napraw będzie sprawdzony na audit/integration, bez scalania do main.
