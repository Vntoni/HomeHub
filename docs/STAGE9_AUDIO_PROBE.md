# Etap 9 — ręczny test mikrofonu i odsłuchu

Użytkownik potwierdził fizyczne wykrywanie ReSpeaker Lite i zmianę ikony
z etapu 8, a także podłączenie głośnika do ReSpeakera. Ten etap dodaje
krótkie nagranie i odsłuch do sprawdzenia toru audio. Nie dodaje AI,
rozpoznawania mowy, automatycznego nasłuchu ani komend urządzeń.

## Obsługa

1. Dotknij ikony mikrofonu w nagłówku HomeHub.
2. Wybierz wejście ReSpeaker. Samo otwarcie panelu nie nagrywa.
3. Naciśnij **Nagraj 5 s** i powiedz kilka słów. Pasek pokazuje poziom
   sygnału; przycisk Stop pozwala zakończyć wcześniej. Czerwona kropka
   przy ikonie oznacza aktywny test (nagrywanie lub odsłuch).
4. Wybierz wyjście ReSpeaker, do którego podłączony jest głośnik lub
   słuchawki, i naciśnij **Odsłuchaj**. Mikrofon wtedy nie nagrywa.
   Głośność próbki jest ustawiona na 40% w strumieniu, bez zmiany
   systemowego miksera. Ostateczna głośność zależy też od systemu i głośnika.
5. **Usuń**, zamknięcie panelu, odłączenie USB, zmiana urządzeń audio
   lub zamknięcie aplikacji zatrzymują test i usuwają próbkę z aplikacji.

Próbka jest tylko w RAM, maksymalnie 5 sekund i 4 MiB. Nie zapisujemy jej
ani transkrypcji na dysku i niczego nie wysyłamy. Odtwarzanie wymaga osobnego
kliknięcia i ma własny limit czasu. Po ponownym podłączeniu nie wznawiamy
nagrywania. W trybie demo audio sprzętowe jest wyłączone.

## Implementacja

- `Ports/audio_probe.py`: kontrakt adaptera i opis formatu PCM Int16.
- `Adapters/qt_audio_probe.py`: Qt Multimedia z istniejącego PySide6;
  import i enumeracja dopiero po otwarciu panelu. Brak nowych pakietów Pythona.
  Na Linuxie Qt Multimedia wymaga biblioteki `libpulse.so.0` (`libpulse0`).
  Dodano ją do runnera CI po odtworzeniu błędu importu; nie instalujemy
  ani nie uruchamiamy serwera PulseAudio. Dostępność biblioteki na Pi
  sprawdza krok importu przed wdrożeniem.
- `Interface/qt_audio_probe.py`: ograniczony bufor, timer, stany testu,
  poziom sygnału i odrzucanie opóźnionych callbacków po zatrzymaniu.
- `AudioProbePopup.qml`: jawny wybór wejścia/wyjścia i akcje testu.
- Backend zamyka audio na wątku Qt przed oczekiwaniem na zasoby urządzeń.

Wejścia filtrujemy po opisie ReSpeaker zwróconym przez system dźwiękowy.
Przed nagraniem wymagane jest też potwierdzenie obecności USB z etapu 8.
Użytkownik wybiera konkretny identyfikator wejścia; nie ma przełączenia
na domyślny mikrofon, kiedy wybrane urządzenie zniknie. Numery kart nie są
wpisane na stałe. Preferujemy natywną częstotliwość i liczbę kanałów urządzenia
z próbkami Int16, w granicach 8–96 kHz i 1–4 kanałów. Dostępne alternatywy
48 kHz stereo / 16 kHz mono również sprawdzamy przez API urządzenia.
Odsłuch wymaga obsługi nagranego formatu przez wybrane wyjście.

USB i wejście audio to dwa osobne stany. Zielona ikona nadal oznacza USB.
Jeśli wejścia nie ma w systemie dźwiękowym Qt, panel pokazuje brak wejścia;
nie zmieniamy automatycznie firmware, sterowników, serwera audio ani miksera.
Błąd audio nie powinien blokować pozostałych paneli HomeHub.

Dokumentacja API: [QAudioSource](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QAudioSource.html),
[QAudioSink](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QAudioSink.html),
[QMediaDevices](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaDevices.html).
Zatrzymanie wyjścia używa `reset()`, aby odrzucić bufor bez czekania na jego
odtworzenie. Natychmiastowe zatrzymanie oraz możliwość importu adaptera
sprawdzamy przed wdrożeniem; mikrofon nie jest otwierany w CI na Pi.

## Testy i granice weryfikacji

Testy offline obejmują: brak automatycznego nagrywania, jawny wybór urządzenia,
brak przejścia na domyślne wejście, limit czasu i rozmiaru, wyrównanie ramek,
ciszę, błędy otwarcia, odłączenie, ponowne podłączenie, późne callbacki,
timeout odsłuchu, half-duplex oraz zakończenie audio przed cleanup urządzeń.
Adapter Qt ma podmienione wszystkie wejścia do sprzętowego audio; sprawdzamy
format, odczyt, bufor pamięci, zakończenie odtwarzania i natychmiastowy reset.
QML jest testowany dotykiem na atrapach, również w 1280×720 i 800×480.

Uruchomienie: `python Tests/check_integrity.py`, `python Tests/run_offline.py`.
Lokalnie: 385 testów jednostkowych/regresyjnych, scenariusz UI i pozostałe
7 scenariuszy smoke. Podczas weryfikacji macOS oznaczał wtyczkę Qt
`offscreen` jako ukrytą; dotknięte tym scenariusze ponowiono po przywróceniu
jej widoczności. Testy nie są pomijane; cały zestaw uruchamia również CI Linux.
Nie wykonano prawdziwego nagrania ani odsłuchu na Pi przez agenta.
Jakość dźwięku, poziom, zgodność wejścia/wyjścia oraz ewentualna cisza przy
Mute wymagają poniższego testu użytkownika po wdrożeniu.

## Test na Pi i dalszy krok

Wykonaj kroki obsługi, sprawdź czy słychać własny głos, a następnie odłącz USB
w trakcie testowego nagrania i upewnij się, że test się kończy. Podłącz ponownie
i wykonaj nowy test. Zamknij panel podczas nagrywania i sprawdź, że po otwarciu
nie ma poprzedniej próbki. Sprawdź też zamknięcie całej aplikacji i pozostałe
panele HomeHub. Nie potrzeba sterować urządzeniami Smart Home podczas próby.

Po potwierdzeniu toru audio kolejnym etapem będzie dobór i pomiar lokalnego
STT po polsku oraz prototyp odczytujący stan; bez sterowania urządzeniami.
Nie rozpoczynamy go automatycznie. Ten etap kończy się testami, scaleniem
na `main`, budowaniem/wdrożeniem i feedbackiem użytkownika.
