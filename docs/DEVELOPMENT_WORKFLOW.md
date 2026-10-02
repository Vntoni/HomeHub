# HomeHub — workflow rozwoju i wdrażania

## Zakres i punkt odniesienia

Ten dokument opisuje bezpieczny workflow dla HomeHub po audycie wykonanym na
snapshotcie z 1 października 2026:

    2552c9b51cc77604af3e3e3c861ad3bd11e5009b

Dokument nie wprowadza napraw funkcjonalnych ani zmian konfiguracji produkcyjnej.
Przyszłe poprawki powinny być wykonywane na czystym checkoutcie tego commita
albo na jego następcy zaakceptowanym w Pull Requeście.

Istniejącego, niezacommitowanego workspace nie należy przełączać na tę historię.
Czysty checkout trzeba utworzyć w osobnym katalogu. Ustawień GitHub, ochrony
branchy ani procesu wdrażania nie zmieniano w tej fazie.

## Model branchy

| Branch | Przeznaczenie | Zasady |
| --- | --- | --- |
| main | stabilna wersja produkcyjna | tylko przez zaakceptowany Pull Request |
| audit/stabilization | testy, obserwacje i przygotowanie stabilizacji | nie wdraża produkcji |
| fix/<nazwa> | jedna niezależna naprawa | branch tworzony z aktualnego celu naprawy |
| feature/<nazwa> | jedna nowa funkcja | funkcja nie może omijać testów i review |

Nazwy powinny opisywać cel, na przykład fix/ac-state-confirmation albo
feature/voice-boundary. Jedna gałąź nie powinna łączyć niezależnych napraw.

## Utworzenie czystego checkoutu od wersji audytowanej

Poniższe polecenia są instrukcją do wykonania w osobnym katalogu. Nie należy
uruchamiać ich w bieżącym, niezacommitowanym workspace:

    git fetch origin main
    git show --no-patch --format='%H %ad %s' --date=iso-strict 2552c9b51cc77604af3e3e3c861ad3bd11e5009b
    git switch -c audit/stabilization 2552c9b51cc77604af3e3e3c861ad3bd11e5009b

Przed zmianą trzeba potwierdzić, że wyświetlony hash jest dokładnie równy
2552c9b51cc77604af3e3e3c861ad3bd11e5009b. Nie używać reset --hard,
wymuszonego pushowania ani automatycznego mergowania.

## Codzienny cykl pracy

1. Zaktualizuj lokalną kopię i sprawdź status oraz bieżący commit.
2. Utwórz branch fix/... albo feature/... z uzgodnionego punktu bazowego.
3. Odtwórz problem w mocku lub symulatorze. Nie steruj prawdziwym urządzeniem
   bez wyraźnej zgody.
4. Dodaj test regresyjny, jeśli zachowanie można wiarygodnie odtworzyć
   automatycznie.
5. Wprowadź najmniejszą zmianę potrzebną do rozwiązania problemu.
6. Uruchom test regresyjny, pełny dostępny zestaw testów i kontrolę składni.
7. Sprawdź git diff, git diff --check oraz pliki konfiguracyjne.
8. Otwórz Pull Request do main i zaczekaj na wymagane kontrole.

Nie należy zmieniać zamierzonego zachowania urządzeń, nazw usług ani danych
produkcyjnych bez osobnej decyzji i opisu wpływu.

## Wymagania Pull Requesta

Opis Pull Requesta powinien zawierać:

- identyfikator problemu i jego priorytet,
- pliki oraz funkcje objęte zmianą,
- kroki odtworzenia i rezultat przed zmianą,
- oczekiwany rezultat po zmianie,
- test regresyjny i pełną komendę używaną do weryfikacji,
- wpływ na QML, konfigurację, integracje lub sprzęt,
- plan wycofania zmiany.

Review powinien potwierdzić, że zmiana nie uruchamia sterowania sprzętem podczas
testów CI, nie ujawnia sekretów i nie omija obsługi błędów.

## Ochrona main

Po potwierdzeniu nazw kontroli w GitHub należy skonfigurować ochronę main:

- wymagany Pull Request przed połączeniem,
- co najmniej jedna akceptacja,
- odrzucanie nieaktualnych akceptacji po nowych commitach,
- rozwiązanie wszystkich rozmów review,
- wymagany status z joba testowego,
- brak bezpośredniego pushowania i force-pushowania,
- brak automatycznego mergowania bez spełnienia kontroli.

Nie należy wpisywać do ochrony nazwy statusu, którego workflow jeszcze nie
wykonał. Ustawień repozytorium nie zmieniano w ramach tej fazy; najpierw trzeba
uruchomić workflow i potwierdzić jego rzeczywiste nazwy statusów.

## Stan workflow CI/CD na wersji audytowanej

Na snapshotcie 2552c9b workflow .github/workflows/ci-cd.yml zawiera:

- job testowy na ubuntu-latest z Pythonem 3.11,
- tryb headless Qt i uruchomienie pytest z coverage,
- krok Tests/ui_smoke.py dla interakcji panelu dotykowego bez sieci,
- osobny job wdrożenia Build & Deploy on RPi5,
- warunek wdrożenia ograniczony do push na main:
  github.ref == 'refs/heads/main' && github.event_name == 'push'.

Z tego wynika, że Pull Requesty oraz branche fix/..., feature/... i
audit/stabilization nie powinny uruchamiać produkcyjnego wdrożenia. Job
wdrożeniowy nie powinien być wymaganym checkiem Pull Requesta. Do ochrony
main należy wybrać wyłącznie zweryfikowany job testowy.

Wdrożenie zachowuje istniejący .env, używa usług systemowych i wykonuje
kontrolę zdrowia usługi. Workflow nie zapewnia automatycznego rollbacku;
procedura poniżej wymaga zachowania poprzedniego commita i ręcznego powrotu.
Nie należy instalować publicznego self-hosted runnera na produkcyjnym
Raspberry Pi ani używać go do testów Pull Requestów z nieufnego kodu.

## Proponowane zmiany workflow

Przed ustawieniem wymaganych statusów należy przygotować osobny Pull Request
z minimalnymi zmianami:

- zachować wyzwalanie testów dla Pull Requestów do main oraz dla pushu na main,
- dodać do joba testowego kontrolę składni przez compileall i podstawową
  kontrolę integralności projektu,
- zachować headless Qt oraz ui_smoke.py jako część wymaganego joba,
- pozostawić wdrożenie wyłącznie pod warunkiem pushu na main po udanym jobie
  testowym,
- ustalić i udokumentować dokładną nazwę statusu joba testowego dopiero po
  pierwszym uruchomieniu workflow,
- nie uruchamiać kodu z Pull Requestów na produkcyjnym self-hosted runnerze.

Rollback wdrożenia powinien być osobnym, przetestowanym zadaniem. Do czasu jego
przygotowania wdrożenie musi zachować identyfikator poprzedniego commita oraz
kopię konfiguracji, aby ręczny powrót był możliwy.

## Komendy weryfikacyjne

Minimalny zestaw lokalny dla zmian Python/QML:

    .venv/bin/python Tests/check_integrity.py
    .venv/bin/python Tests/run_offline.py
    git diff --check

Testy muszą używać mocków i izolowanej konfiguracji. Sekrety, produkcyjny
.env i adresy prawdziwych urządzeń nie mogą być wymagane przez CI.

## Procedura testu na Raspberry Pi

Aktualna, szczegółowa procedura jest w [RASPBERRY_PI_TESTING.md](RASPBERRY_PI_TESTING.md).
Testy offline uruchamiać pod osobnym kontem bez zmiany produkcyjnej usługi.
Testy sprzętowe wymagają zatwierdzonej listy urządzeń i poleceń; samo skopiowanie
.env nie izoluje aplikacji. Powrót wymaga zachowania działającego artefaktu,
konfiguracji i definicji usługi, a nie tylko SHA.

## Checklista gotowości branchy do main

- [ ] branch jest oparty na uzgodnionym commicie,
- [ ] problem można odtworzyć albo wyjaśniono, dlaczego nie jest odtwarzalny,
- [ ] istnieje test regresyjny, jeśli jest technicznie możliwy,
- [ ] wymagane testy, coverage i kontrola składni zakończyły się powodzeniem,
- [ ] ui_smoke.py lub ręczna weryfikacja QML obejmuje dotknięte widoki,
- [ ] testy integracyjne obejmują niedostępność usług i ponowne połączenie,
- [ ] wykonano test Raspberry Pi, gdy zmiana dotyczy sprzętu,
- [ ] sprawdzono, że sekrety i produkcyjne dane nie trafiły do commita,
- [ ] Pull Request ma opis przyczyny, ryzyka i rollbacku,
- [ ] workflow Pull Requesta nie uruchomił produkcyjnego wdrożenia,
- [ ] istnieje możliwy do wykonania powrót do poprzedniej wersji.

## Stan po przygotowaniu fazy 3

Utworzono czysty worktree HomeHub-phase3 na branchu audit/test-environment
od 2552c9b. Poprzedni lokalny audit/stabilization zawiera niezacommitowaną pracę
i pozostał nietknięty. Plan, komendy i wyniki: [TEST_PLAN.md](TEST_PLAN.md).
Propozycja workflow jest poza .github/workflows; nie została uruchomiona na GitHub.
Zatwierdzenie fazy 3 nie oznacza zgody na merge ani produkcyjne wdrożenie.
