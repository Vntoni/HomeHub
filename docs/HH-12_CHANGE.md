# HH-12 — wspólny cykl życia operacji urządzeń

## Problem

Polecenia wysyłane do urządzeń korzystały z kilku niezależnych mechanizmów
blokowania i timeoutów. Po timeoutcie UI zadanie mogło zostać anulowane, mimo że
wywołanie synchronicznego SDK nadal wykonywało się w wątku. Kolejne kliknięcie
mogło wtedy wejść w konflikt z aktywnym klientem transportowym, a panel nie miał
jednego stanu informującego o trwającej operacji.

## Zmiana

Dodano `App.operations.OperationCoordinator`, który:

- rejestruje aktywną operację per urządzenie lub współdzielony klient,
- odrzuca konkurencyjne zapisy i współdzieli równoległe odczyty tego samego
  urządzenia,
- rozdziela timeout oczekiwania UI od faktycznego zakończenia pracy SDK,
- uruchamia późniejszy odczyt potwierdzający po zakończeniu spóźnionego
  transportu,
- zamyka aktywne zadania podczas zamykania backendu.

Operacje blokujące SDK korzystają ze wspólnego `run_blocking()`. Anulowanie
oczekiwania nie przerywa bezpiecznie pracy wątku; koordynator nadal traktuje
zasób jako zajęty do czasu jego rzeczywistego zakończenia.

Backend emituje `deviceOperationBusyChanged`. Karty urządzeń i formularze
ustawień blokują kolejne akcje podczas aktywnego transportu, również po timeoutcie
oczekiwania. Grzejniki korzystają z jednego klucza operacji, ponieważ współdzielą
klienta Atlantic.

## Testy

Wykonano:

- testy koordynatora timeoutu, współdzielenia odczytów i zamykania zasobów,
- test integracyjny backendu z blokującym klientem Atlantic,
- istniejące testy poleceń backendu i panelu: `25 passed`.

Testy nie używają fizycznych urządzeń ani prawdziwych danych uwierzytelniających.
Pełny przebieg QML dla tej gałęzi wymaga ponownego uruchomienia w środowisku z
dostępem do Qt; poprzednia próba została odrzucona przez limit środowiska
uruchomieniowego, więc nie traktuję jej jako zaliczonej.

## Ryzyko i ograniczenia

Zmiana obejmuje wspólną ścieżkę operacji AC, bojlera i grzejników. Nie zmienia
protokołów urządzeń ani nie uruchamia prawdziwego sprzętu. Do potwierdzenia
pozostaje pełny headless smoke test QML na tej konkretnej gałęzi oraz testy na
Raspberry Pi z izolowaną konfiguracją.
