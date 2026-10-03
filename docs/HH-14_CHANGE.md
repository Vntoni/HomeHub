# HH-14 — kontrakt konfiguracji i wersje środowiska testowego

README wskazywał PyQt6, choć aplikacja używa PySide6; przykłady .env pomijały
DB, pogodę i sensory. Uzupełniono oba przykłady bez zmiany konfiguracji ani
wartości domyślnych produkcji. Test AST sprawdza pokrycie kluczy Settings,
a test z fikcyjnymi ścieżkami sprawdza wybór pierwszego .env bez odczytu sekretów.

Kolejność .env pozostaje: katalog sys.executable, ~/.config/bazadomowa/.env,
Config/.env. Wartości istniejące w środowisku nie są nadpisywane przez dotenv.
Główny .env w katalogu repozytorium nie jest osobnym kandydatem w tym kodzie.

requirements-test-constraints.txt zapisuje bezpośrednie wersje zależności
sprawdzone lokalnie i przeznaczone do sprawdzenia w Linux CI. Nie jest pełnym
lockiem zależności przechodnich ani blokadą produkcyjną ARM. requirements.txt
i rzeczywisty .env na Raspberry Pi pozostają bez zmian.

Ograniczenie: brak dostępnego połączenia SSH do Pi w tej sesji; wersje produkcji
nie są potwierdzone. Produkcyjny lock wymaga inwentaryzacji istniejącego venv na
Pi i weryfikacji builda ARM, zgodnie z planem HH-14. Nie wolno zastępować go
listą pakietów z macOS. Odczyt wersji nie wymaga sterowania urządzeniami.
