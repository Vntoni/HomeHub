# HH-02 — zgodność odświeżania z pyairstage

Przyczyna: w pyairstage 3.2.2 `refresh_parameters` synchronicznie parsuje
przekazane dane. Wywołanie bez danych i oczekiwanie na nie jak na korutynę
nie realizuje poprawnie pobrania stanu z chmury.

Odtworzenie offline: adapter z rzeczywistą klasą AirstageAC i fake ApiCloud,
którego `get_devices()` zwraca dwa urządzenia o różnych stanach. Przed naprawą
test odświeżenia nie przechodził; oczekiwany jest niezależny stan każdego ID
po zakończeniu asynchronicznego odczytu.

Adapter czeka teraz na `get_devices()`, wybiera własne ID, sprawdza strukturę
parametrów i przekazuje głęboką kopię do parsera SDK, który mutuje wejście.
Nieprawidłowa struktura nie nadpisuje poprzedniego cache. Starszy kontrakt
asynchronicznego `refresh_parameters()` zachowano osobną ścieżką.

`Tests/Unit/test_ac_refresh_contract.py` sprawdza dwa urządzenia, brak mutacji
odpowiedzi, nieprawidłowe dane, timeout i późniejsze odzyskanie oraz starszy
kontrakt async. Testy przechodzą w pełnym zestawie integracji. Nie wykonywano
odczytów prawdziwej chmury ani sterowania sprzętem.

Ryzyko: niezweryfikowana wersja SDK na Pi lub zmiana struktury odpowiedzi
usługi. Wymagana weryfikacja wersji i izolowany scenariusz sprzętowy przed
wdrożeniem. HH-01 polega na tej poprawce; ewentualny rollback trzeba rozpatrywać
wspólnie z zależnymi zmianami, bez cofania danych ani resetowania main.
