# Awaria startu po dodaniu pozycji nawiewu

Potwierdzona przyczyna z logu Pi: ImportError dla VerticalSwing8PositionsValues.
Środowisko testowe pyairstage 3.2.2 udostępnia tę klasę, zainstalowane SDK Pi
jej nie posiada. Obowiązkowy import opcjonalnej funkcji przerywał uruchamianie
całej aplikacji przed inicjalizacją urządzeń.

Odtworzenie: dwa testy usuwające tę klasę z modułu SDK odtworzyły dokładny
ImportError przed poprawką (2 failed). Adapter teraz pobiera tabelę pozycji
przez getattr dopiero podczas odczytu możliwości. Brak obsługi ośmiu pozycji
nie blokuje importu ani modeli z czterema/sześcioma pozycjami. Nie aktualizujemy
produkcyjnego SDK. Pozostałe funkcje i obsługa czujnika łazienki pozostają.

Workflow przed buildem i zatrzymaniem aplikacji sprawdza import adaptera
w rzeczywistym venv Pi oraz wypisuje wersję SDK. Ten test nie tworzy klientów
ani połączeń z urządzeniami. Nie zastępuje pełnego testu binarnego artefaktu.
Regresje starszego SDK, wszystkie testy offline i QML sprawdzane przed merge;
końcowe potwierdzenie naprawy wymaga udanego kroku Start app service na Pi.
