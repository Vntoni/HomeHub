# Polska mowa i droga do rozmowy z HomeHub

## Rozpoznana przyczyna i granice diagnozy

Użytkownik potwierdził wyraźny odsłuch całego zdania. Aktualna konfiguracja
produkcyjna używała wielojęzycznego Whisper tiny, języka pl i dwuwątkowego
whisper.cpp 1.9.4. Przykład błędu: „klimanyzapja” zamiast „klimatyzacja”.
Jakość modelu to główny podejrzany; bez tego samego nagrania i metryk nie można
wykluczyć problemów kanałów/miksowania, akustyki ani innych błędów toru audio.
Nie zmieniamy formatu wejścia ani nie podkręcamy głośności w ciemno.

Dotychczasowe odpowiedzi były parserem kilku zamkniętych wzorców pytań, a nie
ogólnym agentem AI. Model mowy rozpoznaje tekst; sam nie zna danych domu.

## Zmiany w tym PR

- Domyślny runtime: multilingual base, około 148 MB, osobny katalog
  `~/.local/share/homehub/voice/whisper-v1.9.4-base`. Model i źródła mają
  weryfikowane SHA256. Istniejący runtime tiny zostaje do rollbacku.
- `--prompt` zawiera wyłącznie nazwy urządzeń/pomiarów/pokoi. Nie zawiera
  liczb, temperatur, stanów ani poleceń, które model mógłby dopisać.
  To wskazówka dekodowania, nie gwarancja poprawnej transkrypcji.
- Język pl, dwa wątki, limit 60 s, CPU i niski priorytet na Pi pozostają.
  Nagrania pozostają w pamięci, do 5 s; nie ma nagrywania ciągłego.
- Interfejs pokazuje nazwę faktycznie skonfigurowanego pliku modelu. Jawne
  WHISPER_CLI/WHISPER_MODEL w .env mają pierwszeństwo. Jeżeli nadal wskazują
  tiny, wymagają świadomej zmiany na base — PR nie nadpisuje prywatnego .env.
- Parser dopuszcza dwie edycje liter wyłącznie dla długich nazw klimatyzacji;
  dla innych słów pozostaje jedna. Maksymalnie jedno poprawione słowo na
  pytanie. Liczby, negacje i czasowniki nie są aproksymowane. Oryginalny
  tekst STT jest widoczny, a „Zrozumiano” oznacza dopasowanie literówki.
- Obsługa uprzejmych wstępów („powiedz mi”, „czy możesz mi powiedzieć”).
  Brak pokoju w rozpoznanym rodzaju pytania daje pytanie doprecyzowujące.
  To jeszcze nie dialog wieloturowy: odpowiedź musi zawierać pełne pytanie.
- Brak odczytu nigdy nie jest zastępowany fikcyjną temperaturą lub stanem.
  Odpowiedzi nadal zaznaczają ostatni znany pomiar i jego niepewną świeżość.

## Weryfikacja rzeczywistego STT

`Tools/benchmark_polish_stt.py` przyjmuje JSON z listą obiektów `wav` i
`reference` (polskie zdanie), odczytuje wskazane pliki PCM16, do 5 s, i
uruchamia rzeczywisty model. Domyślnie wypisuje wyłącznie WER, liczbę błędów,
liczbę dokładnych zdań i czasy; nie zapisuje audio ani rozpoznanego tekstu.

    python Tools/benchmark_polish_stt.py /sciezka/cases.json
    python Tools/benchmark_polish_stt.py /sciezka/cases.json --without-prompt
    python Tools/benchmark_polish_stt.py /sciezka/cases.json --model /sciezka/ggml-tiny.bin --without-prompt

Lokalne porównanie użyło ośmiu syntetycznych zdań (macOS Zosia, 190 słów/min,
PCM16 mono 16 kHz). Próbki są tylko w katalogu tymczasowym komputera i nie
są dołączone do repozytorium. Zawierają klimatyzację włączoną/wyłączoną,
negację, temperaturę, wilgotność, prąd i nieobsługiwaną sypialnię. Ta mała próba
mierzy działanie toru na syntetycznej mowie. Nie jest pomiarem akcentu,
pogłosu, odległości od ReSpeakera ani czasu odpowiedzi Raspberry.

Wyniki tej próby na Macu (CPU, dwa wątki; nie Raspberry Pi):

| Konfiguracja | Błędy słów / 42 | WER | Dokładne zdania / 8 | Mediana czasu |
| --- | --- | --- | --- | --- |
| tiny bez słownika | 10 | 23,81% | 2 | 0,573 s |
| tiny ze słownikiem | 8 | 19,05% | 3 | 0,710 s |
| base bez słownika | 6 | 14,29% | 4 | 1,218 s |
| base ze słownikiem | 3 | 7,14% | 6 | 1,162 s |

WER porównuje słowa po ujednoliceniu wielkości liter i pominięciu interpunkcji;
polskie znaki są zachowane. Mała syntetyczna próba nie uzasadnia obietnicy
rozpoznawania każdego zdania. Zmienność czasu między próbami jest normalna.

Test wdrożeniowy nadal wykonuje publiczną próbkę JFK i ciszę przed podmianą
aplikacji. Sprawdza uruchomienie/resampling/wyjście CLI, nie polską dokładność.
Na Pi należy porównać co najmniej 20 własnych zdań (te same nagrania dla
obu modeli): ważne słowa, negacje, brak mowy, cicha mowa i różne odległości.
Zmierzmy medianę i p95 opóźnienia, RSS oraz płynność panelu podczas STT.
Jeżeli base jest nadal niewystarczający, porównamy small z identyczną próbą;
nie wybieramy większego modelu wyłącznie po nazwie.

## Docelowa rozmowa — proponowana kolejność

1. **Wiarygodny tekst.** Porównanie base na własnym głosie, następnie VAD
   (wykrywanie końca wypowiedzi) i sygnalizacja przesterowania/szumów. Sama
   obecność sygnału nie dowodzi obecności mowy; model może halucynować w ciszy.
2. **Odpowiedź przez głośnik.** Lokalny TTS, np. Piper, odczytuje gotową
   odpowiedź. Początkowo tryb naprzemienny: mikrofon wyłączony podczas
   odtwarzania, Stop przerywa wypowiedź. Wake word i usuwanie echa to kolejny
   krok, nie samo uruchomienie nieskończonego nasłuchu.
3. **Szerszy dostęp do danych.** Osobny interfejs tylko do odczytu:
   `get_room_conditions(room)`, `get_device_state(device)`,
   `get_energy_usage(period, date)`. Wynik ma wartość, jednostkę, źródło,
   czas pomiaru/pobrania i informację o brakach. Sekrety i klienci urządzeń
   nie trafiają do modelu. Ten PR nie rozszerza zakresu danych o boiler,
   grzejniki ani energię; te funkcje wymagają tych interfejsów i testów.
4. **Naturalne pytania i kontekst.** Model językowy proponuje intencję i
   argumenty z zamkniętego schematu. Aplikacja waliduje je i wykonuje tylko
   dozwolone odczyty. Liczby w odpowiedzi pochodzą z wyniku funkcji, nie
   z pamięci modelu. LLM można uruchomić na mocniejszym komputerze w LAN;
   nie zakładamy, że równoczesne STT+LLM+TTS zapewni płynność na Pi 5.
5. **Rozmowa wieloturowa.** Krótki, wygasający kontekst pokoju i pytania,
   np. „Jaka temperatura?” → „W którym pokoju?” → „W salonie”. Brak
   jednoznaczności daje doprecyzowanie. Nieznany odczyt → „Nie mam danych”.
   Pytanie poza zakresem → „Tego nie wiem / nie mam takiej funkcji”. Nie
   obiecujemy, że sam prompt LLM wyeliminuje zmyślanie; walidujemy odpowiedzi.

Obecna autoryzacja dotyczy poprawy rozpoznawania i projektu rozmowy o danych.
Nie dodajemy komend sterowania grzaniem ani wysyłania nagrań do chmury.

## Źródła techniczne

- [whisper.cpp CLI 1.9.4 — prompt, język, dekodowanie](https://github.com/ggml-org/whisper.cpp/blob/v1.9.4/examples/cli/cli.cpp)
- [Modele ggml i rozmiary](https://huggingface.co/ggerganov/whisper.cpp)
- [Whisper — modele, języki i różnice dokładności](https://github.com/openai/whisper#available-models-and-languages)
- [Piper — lokalny TTS](https://github.com/OHF-Voice/piper1-gpl)
- [llama.cpp — lokalne uruchamianie LLM](https://github.com/ggml-org/llama.cpp)
