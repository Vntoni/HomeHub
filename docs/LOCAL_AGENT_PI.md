# Lokalny agent — Raspberry Pi 5, 4 GB

Pierwszy etap: LFM3-1.7B Q4_K_M interpretuje pytania w istniejącym panelu mowy
(głos → Whisper → tekst lub wpisanie pytania). Odpowiedź jest tekstowa i pochodzi
wyłącznie z cache HomeHub. Obsługiwane: temperatura, wilgotność, stan AC oraz
swobodne polskie pytania, temperatura i wilgotność razem oraz dopowiedzenia.
Przy niejasnym pomiarze agent dopytuje, zachowując znane pomieszczenie. Kontekst wygasa po 300 s i po zamknięciu panelu.
Nie ma jeszcze TTS, ciągłego nasłuchiwania, sterowania ani zapytań o energię/boiler/grzejniki.
Model nie otrzymuje haseł, pomiarów ani dostępu do urządzeń. Nie jest uruchamiany na Macu.

## Instalacja na Pi

Po wdrożeniu main przez Actions, w checkout repo na Pi, jako `miggie`:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git curl ca-certificates
bash Tools/install_local_agent.sh
curl --fail http://127.0.0.1:9081/health
```

Instalator wymaga Linux ARM64. Buduje przypiętą wersję llama.cpp b11960 (2 zadania
kompilacji), pobiera model ok. 1,1 GB z przypiętej rewizji producenta, sprawdza SHA256.
Potrzebne kilka GB wolnego miejsca na źródła, kompilację i model. Kompilacja może potrwać.
Przy braku systemowego CMake instalator pobiera CMake 3.31.6 do osobnego venv.
Nie uruchamia się automatycznie w CI/CD; kolejne deploye aplikacji nie przebudowują modelu.
Usługa użytkownika `homehub-agent` startuje po zalogowaniu; aby startowała także po
restarcie bez logowania: `sudo loginctl enable-linger miggie`.
Model nasłuchuje wyłącznie na 127.0.0.1:9081 (Zigbee2MQTT zachowuje port 8080).

## Pomiar przed włączeniem

Zostaw HomeHub otwarty. Użyj Pythona 3.11+ ze środowiska projektu z httpx:

```bash
python3 Tools/benchmark_local_agent.py --output ~/lfm3-3threads.json
```

Jeśli systemowy Python nie ma httpx, użyj istniejącego venv projektu albo:

```bash
python3 -m venv ~/.local/share/homehub/agent/bench-venv
~/.local/share/homehub/agent/bench-venv/bin/pip install 'httpx>=0.27,<1'
~/.local/share/homehub/agent/bench-venv/bin/python Tools/benchmark_local_agent.py --output ~/lfm3-3threads.json
```

Test obejmuje 41 pytań, poprawność intencji, medianę/p95 czasu HTTP, dostępną pamięć
systemu i RSS/peak RSS serwera (peak od jego startu). To NIE jest pomiar STT/TTS ani
płynności UI; podczas testu sprawdź reakcję ekranu ręcznie. Kod wyjścia 1 oznacza błędy
klasyfikacji lub niedostępny model — zachowaj JSON. Nie traktuj samej poprawności JSON
jako poprawnego zrozumienia pytania. Nie ma jeszcze wyników pomiarów z tego Raspberry.

## Włączenie w głównej aplikacji

W `~/.config/bazadomowa/.env` ustaw pojedynczy wpis:

```dotenv
HOMEHUB_LOCAL_AGENT=1
```

Jeżeli obok binarnego pliku aplikacji istnieje `.env`, ma pierwszeństwo — ustaw wpis tam.
Następnie `systemctl --user restart bazadomowa` i otwórz panel mowy.
Sprawdź: „Jak ciepło jest w łazience?”, „A wilgotność?”, „A w salonie?”.
Dla braku pomiaru aplikacja zgłasza brak danych; nie odczytuje liczb z wypowiedzi modelu.
Model może błędnie wybrać pomieszczenie/intencję: sprawdź pole interpretacji w panelu.
Awaria modelu nie blokuje klasycznych pytań, np. „Temperatura w łazience”.

## Porównanie i powrót

Domyślnie: CPU, 3 wątki, kontekst 2048, jeden slot, maks. 80 tokenów, bez rozumowania.
W `~/.config/systemd/user/homehub-agent.service` można zmienić `--threads` oraz
`--threads-batch` na 2, potem 4. Po każdej zmianie:

```bash
systemctl --user daemon-reload
systemctl --user restart homehub-agent
# Poczekaj, aż /health zwróci 200, potem benchmark z inną --label i --output.
```

Porównuj medianę/p95 i poprawność przy tych samych pytaniach i działającym HomeHub.
Kolejne modele można podłączyć przez ten sam endpoint i alias `homehub-local`;
trzeba osobno dobrać zgodny szablon rozmowy i wyłączyć rozumowanie.
Limity usługi: MemoryHigh=1700M, MemoryMax=2200M, MemorySwapMax=0; to budżet,
nie zmierzony pobór pamięci. Jeśli proces jest zabijany przez limit, zapisz logi
zamiast zwiększać limit kosztem aplikacji.

Powrót: ustaw `HOMEHUB_LOCAL_AGENT=0`, zrestartuj `bazadomowa`, potem
`systemctl --user disable --now homehub-agent`. Model pozostaje na dysku.
Logi: `journalctl --user -u homehub-agent -n 80 --no-pager`.

Źródła: https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF
oraz https://github.com/ggml-org/llama.cpp/tree/b11960/tools/server.

## Uruchomienie przez GitHub Actions

Po udanym wdrożeniu main można uruchomić workflow **Local AI benchmark on RPi5**.
Korzysta z tego samego runnera i venv co wdrożenie, instaluje model i zapisuje JSON jako
artefakt. Wymagane narzędzia kompilacji muszą już być na Pi (patrz instalacja).
Opcja `enable_in_app` włącza AI dopiero po przejściu wszystkich przypadków benchmarku.
Tworzy `~/.config/systemd/user/bazadomowa.service.d/20-local-agent.conf` — ten wpis
ma pierwszeństwo przed `.env`. Aby cofnąć takie włączenie, usuń wyłącznie ten plik,
wykonaj `systemctl --user daemon-reload` i zrestartuj `bazadomowa`.


Klient na przypiętej wersji b11960 używa zwykłej generacji: wymuszanie JSON w serwerze
powoduje błąd dekodera na dodatkowym pustym znaczniku `</think>`. Aplikacja usuwa tylko
ten znacznik, następnie sprawdza cały obiekt JSON, jego klucze i dozwolone wartości.
Nie akceptuje tekstu objaśniającego, dodatkowych pól ani liczb pochodzących od modelu.

Dla Pi 4 GB ustawiono batch/ubatch=128, 4 checkpointy z odstępem 128 tokenów i cache
ograniczony do 128 MiB. Domyślny odstęp 8192 nie pomagał w kontekście 2048 tokenów.
Pozwala to ponownie wykorzystać wspólny prompt w modelu z warstwami rekurencyjnymi.
Pomiary zimnego i kolejnych żądań nadal należy odróżniać; w benchmarku pierwszy
przypadek może być wolniejszy.


Po udanym pełnym benchmarku można użyć `activation_only=true` oraz `enable_in_app=true`
w workflow Local AI benchmark on RPi5. Nadal weryfikuje runtime i trzy pytania, ale nie
powtarza pełnego pomiaru. Stosuj tę opcję dla tej samej sprawdzonej wersji klienta i modelu.
W logu uruchomienia aplikacji pojawia się `HomeHub voice answers: local LFM3 enabled`
lub `basic parser`, co pozwala odróżnić faktycznie używany tryb od samej obecności modelu.
