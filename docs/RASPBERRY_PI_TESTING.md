# Testy HomeHub na Raspberry Pi — procedura do zatwierdzenia

Nie wykonywano tej procedury na sprzęcie. Testy offline opisane w TEST_PLAN.md
nie wymagają zgody na sterowanie urządzeniami. Każdy etap korzystający z
prawdziwych integracji wymaga osobnego zatwierdzenia scenariusza i urządzeń.

## 1. Identyfikacja i przygotowanie

- Zanotować commit wdrożonej wersji, wersje Python/Qt/pyairstage oraz architekturę
  systemu. Jeżeli commit wdrożonego pliku binarnego nie jest znany, nie zakładać,
  że odpowiada HEAD repozytorium; zachować działający artefakt jako punkt powrotu.
- Odczytać definicję usługi bazadomowa bez jej zmieniania. Logi i konfiguracja
  mogą zawierać identyfikatory i sekrety; zapisywać tylko zredagowane wyniki.
- Użyć osobnego konta systemowego do testów, osobnego katalogu checkoutu,
  venv, konfiguracji i danych. Nie uruchamiać testów jako użytkownik produkcji.
- Sprawdzić status Git przed przygotowaniem checkoutu; użyć konkretnego SHA
  zatwierdzonego brancha fix/..., bez resetu, force push i mergowania main.
- Nie wykonywać deploy_baza.sh, build/deploy joba ani restartu produkcyjnej
  usługi w ramach weryfikacji offline. Nie instalować runnera na produkcyjnym Pi.

## 2. Etap offline na Pi

1. W nowym koncie/katalogu zainstalować zatwierdzone zależności do osobnego venv.
   Nie aktualizować środowiska działającej usługi.
2. Uruchomić Tests/check_integrity.py i Tests/run_offline.py. Nie kopiować .env.
3. Zapisać logi, JUnit, coverage, SHA, wersję OS/Python/Qt/SDK i czas uruchomienia.
4. Powtórzyć startup/stop demo, weryfikując brak pozostawionych procesów testowych.
5. Test wizualny/dotyku wymaga osobnej sesji graficznej lub uzgodnionego okna,
   aby nie zajmować ekranu produkcyjnej aplikacji. Sprawdzić skalowanie, fokus,
   dotyk krawędzi przycisków, responsywność i komunikaty błędów.

## 3. Izolowane integracje

Przed uruchomieniem produkcyjnego composition root trzeba zidentyfikować
wszystkie jego skutki startowe. Samo uruchomienie może rozpocząć MQTT, zapisy
DB, odpytywanie chmur i BLE, w tym zapisy inicjalizujące GATT. Obecny kod nie
gwarantuje przełącznika „tylko odczyt”. Nie używać go jako testu read-only.

Konfigurację testową przygotować od zera z przykładu, z uprawnieniami 0600.
Obecny loader wybiera pierwszy istniejący .env: obok interpretera/binarnego
pliku, w katalogu konfiguracji konta, potem Config/.env. Pod testowym kontem
zweryfikować wszystkie trzy lokalizacje i brak odziedziczonych zmiennych.
Nie kopiować produkcyjnego .env do testów.

MQTT ma obecnie adres brokera wpisany w adapterze. Sama zmiana .env nie
izoluje tej integracji. Do testów rzeczywistego transportu potrzebny jest
oddzielny host/kontener z testowym brokerem lub późniejsza zatwierdzona
konfigurowalność adaptera. Używać własnego prefiksu topiców i fikcyjnych ID.

PostgreSQL: osobna jednorazowa baza i konto bez praw do bazy produkcyjnej.
Osobny DSN musi być zweryfikowany przed connect (adapter tworzy tabele).
Nie używać kopii bazy zawierającej dane domowe. Przywracanie backupu ćwiczyć
wyłącznie w bazie testowej, nigdy nad produkcyjną.

Chmury i BLE: lista dopuszczonych urządzeń, dokładnych poleceń, zakresów
temperatur i warunków przerwania musi być zatwierdzona przed testem.
Nie da się uznać prawdziwego urządzenia za izolowane tylko przez skopiowanie
konfiguracji. Nie uruchamiać dwóch kontrolerów wysyłających sprzeczne komendy.

## 4. Scenariusz sprzętowy AC po odrębnej zgodzie

- Zapisać stan początkowy i uzgodniony sposób jego odtworzenia po teście.
- Sprawdzić jedno zatwierdzone urządzenie i jedno polecenie. Porównać UI,
  odczyt chmury i niezależną obserwację urządzenia. ON oznacza zasilanie,
  nie dowód pracy sprężarki.
- Sprawdzić opóźnienie potwierdzenia, błąd odczytu i odzyskanie połączenia.
  Awarię symulować dla procesu testowego; nie wyłączać Wi-Fi/brokera całego domu.
- Zapisać czasy: kliknięcie, przyjęcie polecenia, readback, aktualizacja QML.
- Przerwać przy nieoczekiwanym urządzeniu, wartości lub niepotwierdzonym zapisie.
  Nie ponawiać automatycznie komendy po timeoutach.
- Przywrócenie stanu urządzenia też jest poleceniem sprzętowym i musi należeć
  do zatwierdzonego scenariusza.

## 5. Powrót po teście i rollback wdrożenia

Zakończenie testów w osobnym koncie powinno wymagać wyłącznie zatrzymania
procesów testowych i sprawdzenia, że produkcja nadal działa. Dane i proces
produkcyjny nie powinny być zmienione.

Jeżeli w przyszłości zatwierdzono test wymagający zastąpienia usługi:

1. Przed zatrzymaniem zachować działający artefakt/binaria, definicję usługi
   wraz z override, konfigurację i kopię danych. Zapisać sumy kontrolne,
   uprawnienia i identyfikator wersji; backup poza katalogiem nadpisywanym
   przez deploy. Sam SHA nie odtwarza binarnego pliku ani danych.
2. Najpierw sprawdzić uruchomienie artefaktu powrotnego w izolowanym środowisku.
   Uzgodnić okno przerwy i kryteria rollbacku.
3. Przy nieskutecznym starcie, błędnych stanach lub nowych wyjątkach zatrzymać
   tylko testowaną usługę, odtworzyć poprzedni artefakt i definicję, uruchomić
   poprzednią wersję i potwierdzić jej działanie oraz poprawność konfiguracji.
4. Nie przywracać bazy automatycznie: restore może nadpisać nowe pomiary.
   Migracje wymagają osobnego planu zgodności i decyzji o odzyskiwaniu danych.

Obecny deploy usuwa poprzedni katalog binarny przed skopiowaniem nowego.
Bez dodatkowego backupu nie stanowi to odwracalnego wdrożenia. Ta faza jedynie
dokumentuje ograniczenie; nie modyfikuje wdrażania ani produkcji.

## Protokół wyniku

SHA / data / operator; model Pi i OS; Python/Qt/SDK; testowy profil bez
sekretów; scenariusz i zatwierdzony zakres; wynik oczekiwany/rzeczywisty;
logi; opóźnienia; stan zasobów po stop; wpływ na produkcję; wynik powrotu.
Brak możliwości wykonania etapu oznaczyć „niewykonany”, nie „PASS”.
