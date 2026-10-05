# Etap 10 — lokalna transkrypcja po polsku

Po potwierdzeniu przez użytkownika nagrywania i odsłuchu dodajemy kolejny
mały krok: **Nagraj 5 s → Rozpoznaj po polsku → tekst na ekranie**.
Tekst nie wywołuje żadnej funkcji urządzeń. Intencje odczytu stanu, TTS,
komendy i wake word pozostają kolejnymi krokami, po ocenie polskiego STT.

## Silnik i prywatność

- Przypięty [whisper.cpp v1.9.4](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.4),
  commit `927cfce34f31707e17f2bff35c349632fb9e2c3a`, model wielojęzyczny
  [ggml-tiny.bin](https://huggingface.co/ggerganov/whisper.cpp/blob/main/ggml-tiny.bin),
  około 78 MB. To wersja startowa do pomiarów, nie deklaracja osiągniętej jakości.
- Proces `whisper-cli`: jawny język `pl`, CPU, 2 wątki, niższy priorytet
  na Linuxie, limit 60 s. Nigdy nie uruchamiamy dwóch sesji jednocześnie.
- WAV powstaje w pamięci i trafia na stdin procesu. miniaudio w przypiętym
  silniku konwertuje format nagrania do mono 16 kHz. Nie tworzymy pliku audio.
- Bufor wejścia do 5 s / 4 MiB, stdout do 16 KiB, tekst do 2000 znaków.
  Treść nie jest logowana, zapisywana ani wysyłana. Proces dostaje minimalne
  środowisko bez haseł urządzeń i zmiennych bibliotek PyInstaller.
- Zatrzymanie, zamknięcie panelu, odłączenie USB i zamknięcie HomeHub anulują
  rozpoznawanie. Najpierw kończymy proces, potem zwalniamy jego zasoby.
  Po 2 s bez reakcji na terminate stosujemy kill. Późny wynik jest ignorowany.
- Rozpoznanie nie uruchamia odsłuchu ani mikrofonu. Próbki bardzo ciche są
  odrzucane przed STT; to prosty próg poziomu, nie detektor mowy. Model może
  rozpoznawać błędny tekst, dlatego na tym etapie niczego nim nie sterujemy.

## Instalacja i wdrożenie

`Tools/install_voice_runtime.py` działa przed zatrzymaniem produkcyjnej aplikacji,
tylko w deployu z zaufanego `main`. Archiwum źródeł i model mają przypięte SHA256
w `Config/voice_runtime.py`. Budujemy tylko CLI, bez GPU i nowych zależności
Pythona aplikacji. Kompilacja korzysta z dwóch procesów, niższego priorytetu;
jeśli brakuje CMake, instalator pobiera narzędzie CMake 3.31.6 do tymczasowego
katalogu budowania. Wymagane są już dostępne g++ i make; brak narzędzi kończy
deploy przed zatrzymaniem działającej aplikacji.

Runtime znajduje się w `~/.local/share/homehub/voice/whisper-v1.9.4-tiny/`.
Instalacja używa katalogu tymczasowego i atomowego przeniesienia gotowej wersji.
Kolejne deploye sprawdzają sumy istniejących plików i nie budują ponownie.
Model/silnik pozostają poza binarium HomeHub i danymi produkcyjnymi.
Opcjonalne ustawienia obecnego loadera `.env`: `WHISPER_CLI`, `WHISPER_MODEL`
(domyślnie ścieżki tego runtime). Brak modelu nie blokuje startu ani nagrywania;
panel wyłącza przycisk STT i pokazuje informację.

`Tools/voice_runtime_smoke.py` uruchamia rzeczywisty proces na Pi, na pętli
qasync używanej przez aplikację, z syntetyczną ciszą stereo 48 kHz / 5 sekund.
Sprawdza też resampling i wypisuje czas oraz maksymalne RSS procesu potomnego.
Nie otwiera mikrofonu, nie ładuje konfiguracji urządzeń ani nie używa nagrań
użytkownika. To test działania i orientacyjny pomiar kosztu, nie pomiar
skuteczności polskiej mowy lub percentyli latencji.

## Testy

OfflineGuard pozostaje włączony. Testy jednostkowe używają fake procesu:
stdin, polski język, ograniczone wątki i środowisko, limit stdout, timeout,
błąd procesu, anulowanie również podczas jego tworzenia oraz brak runtime.
Kontroler: brak automatycznego STT, jeden proces, cisza, błąd z możliwością
ponowienia, kasowanie tekstu i oczekiwanie na zakończenie przy zamykaniu.
QML: przycisk i polski tekst z atrapy, ekrany 1280×720 i 800×480, bez audio
sprzętowego. Osobny rzeczywisty test procesu na Pi nie wyłącza OfflineGuard
w suite aplikacji.

## Test użytkownika po wdrożeniu

Nagraj np. „Jaka jest temperatura w łazience?”, naciśnij **Rozpoznaj po polsku**
i sprawdź tekst oraz pokazany czas. Powtórz z 3–5 własnymi zdaniami. Sprawdź
anulowanie przyciskiem Stop i zamknięciem panelu. Zgłoś błędne słowa i czas;
na tej podstawie porównamy tiny z większym modelem, zamiast zakładać z góry,
że większy model będzie wystarczająco szybki na tym Pi.

Powrót do poprzedniego artefaktu HomeHub nie wymaga usuwania runtime — starsza
aplikacja go nie używa. Ten etap kończymy wdrożeniem na main i opinią użytkownika.
