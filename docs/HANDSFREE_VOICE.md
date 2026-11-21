# Rozmowa głosowa na Raspberry Pi

Po wdrożeniu aplikacja ma lokalny głos Piper Gosia (polski, medium) i nasłuch hasła
„Gugu gaga”. Runtime Piper 1.8.0 i model są instalowane przez CI przed wymianą aplikacji.
Model głosu ma przypiętą rewizję i SHA256, dane treningowe Gosia mają licencję CC0.
Nie potrzeba Maca, serwera w chmurze ani konta TTS.

1. Po podłączeniu ReSpeakera aplikacja wybiera zapisane urządzenia. Przy pierwszym
   uruchomieniu wybiera jedyny ReSpeaker i jego wyjście (lub domyślny głośnik systemu).
   Jeśli wybór jest niejednoznaczny, otwórz panel mikrofonu i wskaż urządzenia.
2. Powiedz **samo „Gugu gaga”**, zrób pauzę i poczekaj na **„Słucham”**.
3. Zadaj pytanie. Pauza ok. 0,7 s kończy wypowiedź. Po rozpoznaniu pytania HomeHub
   odpowiada przez głośnik i sam wraca do słuchania kolejnego pytania.
4. Powiedz ponownie **„Gugu gaga”**, gdy agent skończy mówić. Usłyszysz potwierdzenie
   zakończenia rozmowy. Nasłuch samego hasła pozostaje aktywny.
5. Przycisk **„Wyłącz nasłuch i mikrofon”** w panelu zatrzymuje całe audio i zapamiętuje
   tę decyzję po restarcie. Zamknięcie panelu samo w sobie nie kończy rozmowy.

Stan jest widoczny na ekranie głównym i w panelu. Do ponownego włączenia użyj przycisku
„Włącz nasłuch hasła”. Wybór urządzeń i włączenie są zapisane przez QSettings w
`~/.config/HomeHub/VoiceConversation.conf`. Rozłączenie USB zatrzymuje audio; ponowne
podłączenie przywraca nasłuch, jeśli był zapisany jako włączony. Zmiana listy urządzeń
podczas rozmowy zatrzymuje ją; nie następuje ciche przełączenie na inny mikrofon.

## Sposób działania i ograniczenia

To pierwsza wersja nasłuchu oparta o lokalny Whisper i wykrywanie energii sygnału,
a nie specjalnie wytrenowany detektor wake word. Cisza nie uruchamia Whispera.
Po wykryciu wypowiedzi sprawdzany jest cały rozpoznany tekst: tylko dokładne „Gugu gaga”
(z tolerancją interpunkcji/spacji) przełącza stan. Szum, telewizor i odległość mogą
pogarszać działanie — konieczna jest próba na rzeczywistym mikrofonie. Rozpoznanie hasła
może trwać kilka sekund. Rozmowa w tle w trybie oczekiwania jest odrzucana po STT,
nie trafia do modelu językowego i nie jest zapisywana na dysku.

Wypowiedź jest ograniczona do 12 sekund. Zbyt długie pytanie nie jest interpretowane
fragmentami: agent prosi o krótsze. Mikrofon jest zatrzymany podczas interpretowania
pytania i odtwarzania odpowiedzi, potem obowiązuje 0,7 s przerwy na wybrzmienie dźwięku.
Nie ma jeszcze przerywania odpowiedzi głosem; przycisk Stop działa natychmiast.
Progu VAD można użyć do kalibracji mikrofonu: `rmsThreshold=0.008` w QSettings
(ułamek pełnej skali Int16, domyślnie 0.008). Zmieniaj go przy zamkniętej aplikacji.

Piper działa w odizolowanym procesie, utrzymuje jeden model, ma 2 wątki CPU i timeout
40 s. Audio przekazywane jest w pamięci, a proces kończy się po wyłączeniu nasłuchu.
Na wyjściu używany jest wybrany głośnik, również przy konwersji 22,05 kHz → 48 kHz.
Nie uruchamiamy kolejnego STT/LLM/TTS równolegle z poprzednim pytaniem.

Zakres wiedzy agenta pozostaje taki jak w panelu pytań: temperatura, wilgotność i stan
klimatyzacji z cache, wraz z informacją o braku/aktualności danych. Swobodne sformułowania
wymagają wcześniej włączonego lokalnego LFM3 (`HOMEHUB_LOCAL_AGENT=1`). Sam tryb głosowy
nie włącza LFM3 ani sterowania urządzeniami; nie zmienia tego, jakie dane są dostępne.

## Próba na Pi

Sprawdź hasło 10 razy z normalnej odległości, również w hałasie. Następnie kilka pytań,
np. „Temperatura w łazience”, „Wilgotność w łazience”, „Stan klimatyzacji w salonie”.
Sprawdź brak samoczynnego wybudzania podczas mówienia agenta, zakończenie hasłem,
przycisk Stop, zamknięcie panelu, restart aplikacji i odłączenie USB podczas odpowiedzi.
Testy automatyczne używają sztucznego audio i atrap; nie zastępują tych prób sprzętowych.
