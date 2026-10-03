# Pozycje nawiewu i czujnik łazienki

Na prośbę użytkownika panel AC udostępnia pionowe pozycje nawiewu oraz
falowanie. SDK pyairstage 3.2.2 zwraca 4, 6 lub 8 pozycji, nie kąty w stopniach.
Opcje zależą od możliwości urządzenia. Stała pozycja wyłącza falowanie,
a opcja Falowanie włącza je bez zmiany pozycji. Niezmienione pole nie wysyła
komendy. Walidacja obejmuje dostępne pozycje, świeży odczyt zasilania i odczyt
po zapisie; brak potwierdzenia zgłasza błąd. Pozostałe urządzenie jest niezależne.

Zigbee: log dostarczony przez użytkownika wskazuje poprawną wiadomość na
zigbee2mqtt/czujnik_lazienka. Poprzednie domyślne pokoje salon,jadalnia nie
tworzyły tej subskrypcji. Dodano lazienka do domyślnych ustawień i do listy
subskrypcji także dla starszych .env. Zachowano pozostałe skonfigurowane pokoje,
nie przepisano produkcyjnych sekretów. Jest to celowe dodanie konkretnego,
potwierdzonego przez użytkownika czujnika, nie automatyczne wykrywanie urządzeń.
Mapa pokazuje temperaturę i wilgotność w polu WC. Pozostałe pokoje bez własnego
pomiaru nadal pokazują brak danych; pomiaru łazienki nie kopiujemy do innych.
Po starcie odczyt pojawi się po następnej wiadomości MQTT (lub retained).

Testy: rzeczywiste SDK z fake transportem dla 4/6/8 pozycji, falowania,
wyłączenia falowania, niedostępnych opcji; backend OFF, walidacja, niezgodny
readback i izolacja pokoju. QML sprawdza wybór falowania i odczyt, a mapa
wartości 20.6°C/65% z przykładowej wiadomości. Test subskrypcji obejmuje starą
konfigurację i duplikaty. Pełny runner offline jest wykonywany przed merge.

Nie wykonywano komend na prawdziwym klimatyzatorze ani połączenia testowego
z brokerem Pi. Log potwierdza publikację w dniu 1 października; aktualną
dostępność brokera i fizyczny ruch żaluzji sprawdzi użytkownik po wdrożeniu.
Zmiana trafia do main po zielonym CI na wyraźne polecenie użytkownika.
