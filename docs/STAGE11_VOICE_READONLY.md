# Etap 11 — pytania o ostatni znany stan domu

Po potwierdzeniu transkrypcji przez użytkownika dodajemy odpowiedź tekstową
na małą listę polskich pytań. Najpierw weryfikujemy rozumienie i odczyty;
TTS, polecenia urządzeń, wake word i LLM pozostają osobnymi etapami.

## Obsługa

W panelu **Zapytaj HomeHub**: Nagraj 5 s → Rozpoznaj po polsku. Pod tekstem
automatycznie pojawią się „Zrozumiano” i odpowiedź. Można też wpisać/poprawić
pytanie i nacisnąć **Sprawdź pytanie** (lub Enter), bez ponownego nagrywania.
Oryginalna transkrypcja pozostaje widoczna. Edycja usuwa poprzednią odpowiedź,
żeby nie sugerować, że dotyczy nowego pytania.

Przykłady:

- „Jaka jest temperatura w łazience?”
- „Jaka jest wilgotność w łazience?”
- „Ile stopni w salonie?”
- „Czy klimatyzacja w salonie jest włączona?”
- „Jaki jest stan klimatyzacji w jadalni?”

Obsługiwane pomieszczenia: salon, jadalnia, łazienka. Brak danych dla danego
pomieszczenia daje jawny komunikat. Inne pytania, komendy, negacje i pytania
o kilka pokoi naraz dają pomoc i prośbę o jednoznaczne pytanie.

## Źródła i świeżość

`VoiceQueryBridge` odbiera istniejące sygnały dashboardu przez sloty QObject
na wątku Qt, również przy MQTT pochodzącym z osobnego wątku. Moduł
`ReadOnlyHomeQueries` przechowuje wyłącznie wartości; nie ma klientów,
transportów, metod komend ani połączenia z bazą. Pytanie nie uruchamia
odświeżenia, zapisu ani komunikacji sieciowej.

Temperatura pochodzi z czujnika Zigbee, a gdy brak jego pomiaru — z dostępnego
odczytu AC w danym pokoju. Źródło zawsze jest nazwane. Wilgotność pochodzi
wyłącznie z czujnika. Stan AC jest wyprowadzany tylko ze znanych trybów:
OFF = wyłączona, AUTO/COOL/DRY/FAN/HEAT = włączona. Nieznany tryb = brak danych.

Odpowiedzi mówią **ostatni znany odczyt/stan**, nie „teraz”. Dla MQTT obecny
interfejs nie podaje czasu wykonania pomiaru: odpowiedź jawnie to zaznacza.
Dla AC wykorzystujemy istniejący sygnał nieaktualności; stan początkowy
jest ostrożnie traktowany jako niepotwierdzony. Nieprawidłowe liczby/None
nie są zerem; rzeczywiste zero jest poprawnym odczytem. Odpowiedź jest
migawką z chwili pytania — przycisk Sprawdź pytanie odczyta nowszy cache.

## Błędy transkrypcji i granice

Model STT pozostaje tiny; ten etap nie deklaruje poprawy jego jakości.
Parser normalizuje wielkość liter i polskie znaki, zna odmiany słów i dopuszcza
maksymalnie jedną literówkę (dodanie/usunięcie/zamiana litery) w długim słowie
z zamkniętej listy nazw pokoi/pomiarów/klimatyzacji. Wymagane jest jednoznaczne
dopasowanie. Dopasowanie literówki jest pokazane w „Zrozumiano”. Nie poprawiamy
automatycznie czasowników, negacji ani liczb. Całe pytanie musi pasować do
jednego wzorca; dodatkowe polecenia lub nieznane słowa powodują odrzucenie.

Maksymalnie 300 znaków / 14 słów, bez eval, shell, dynamicznego wywoływania
metod lub nowych zależności. Pytania i odpowiedzi pozostają w pamięci;
nie trafiają do logów, plików ani chmury. Nowe nagranie, zamknięcie panelu,
odłączenie USB i zamknięcie aplikacji usuwają je razem z próbką. Późny wynik
STT po anulowaniu nie tworzy odpowiedzi. Pola odpowiedzi w QML są PlainText.

## Weryfikacja i test ręczny

Testy offline obejmują wzorce pytań, pojedyncze literówki, niejednoznaczność,
negacje/komendy, zero/brak/NaN, źródło pomiaru, dane nieaktualne, aktualizacje
sygnałami Qt (także z wątku), brak wywołań urządzeń, edycję, zamknięcie i późny
wynik STT. QML sprawdza automatyczną odpowiedź oraz zmianę pytania na wilgotność
na ekranach 1280×720 i 800×480. Pełny zestaw zachowuje OfflineGuard.

Po wdrożeniu sprawdź trzy przykładowe pytania, porównaj odpowiedzi z panelem
HomeHub i popraw jedno błędnie rozpoznane słowo w polu tekstowym. Zapisz czas
rozpoznawania i przykłady przekręconych słów; na tej podstawie ocenimy potrzebę
większego modelu. Jakość rzeczywistej polskiej mowy i tor audio na Pi wymagają
testu użytkownika. Nie wykonujemy automatycznych komend sprzętowych.

Następny proponowany etap po potwierdzeniu odczytów: lokalny odczyt odpowiedzi
przez głośnik (TTS). Zmiany ustawień urządzeń dopiero z osobnym potwierdzeniem
na ekranie i testami istniejącej obsługi komend.
