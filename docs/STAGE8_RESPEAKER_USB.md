# Etap 8 — opcjonalny ReSpeaker Lite: obecność USB

W nagłówku HomeHub jest jedno miejsce na mikrofon z dwiema ikonami:

- czarna, przekreślona: urządzenie niepodłączone lub nie można potwierdzić jego obecności;
- turkusowa: wykryto ReSpeaker Lite na USB.

Dotknięcie ikony pokazuje opis stanu. Dodatek nie nagrywa, nie otwiera
strumienia audio, nie steruje urządzeniami i nie wymaga nowych bibliotek.
HomeHub działa również bez ReSpeakera. Stan jest sprawdzany w tle,
niezależnie od otwartych paneli i odświeżania urządzeń co 15 minut.

## Implementacja i ograniczenia

`RespeakerUsbAdapter` odczytuje deskryptory Linux sysfs
(`/sys/bus/usb/devices`) i rozpoznaje VID:PID `2886:0019`.
Identyfikator pochodzi z [instrukcji producenta](https://github.com/respeaker/reSpeaker_Lite/blob/master/xmos_firmwares/dfu_guide.md).
Nie rozpoznajemy dowolnego mikrofonu USB jako ReSpeakera.

`RespeakerService` wykonuje odczyt poza wątkiem interfejsu, następnie czeka
2 sekundy przed kolejnym sprawdzeniem. Backend przekazuje zmiany do QML
przez właściwości i sygnał. Monitor jest pojedynczym zadaniem zarządzanym
przez istniejący mechanizm zamykania aplikacji. Zamknięcie czeka również
na zakończenie rozpoczętego odczytu, bez późniejszej aktualizacji UI.
Błąd odczytu nie zatrzymuje aplikacji; kolejne próby pozwalają odzyskać stan.

Kolor potwierdza **obecność USB**, a nie działanie mikrofonu, stan jego
wyciszenia ani gotowość firmware do nagrywania. Ten identyfikator może być
widoczny również w innych trybach firmware. Nie zmieniamy firmware,
sterowników, uprawnień USB ani produkcyjnej konfiguracji audio.
Poza Linuksem brak sysfs skutkuje informacją o braku obsługi wykrywania.
Tryb demonstracyjny domyślnie nie sprawdza rzeczywistego USB.

## Weryfikacja

Testy korzystają z tymczasowych deskryptorów USB i atrap: wykrycie,
odłączenie w trakcie odczytu, ponowne podłączenie do innego portu,
odrzucenie innych urządzeń, brak dostępu, odzyskanie po błędzie,
wykonywanie odczytu poza wątkiem UI i zamknięcie w trakcie odczytu.
Test QML sprawdza oba zasoby SVG, przejścia stanu bez restartu oraz
istniejące ekrany i rozmiary okna. Zrzuty trafiają do `test-results/ui`.

Polecenia: `python Tests/check_integrity.py` oraz
`python Tests/run_offline.py`. Lokalny wynik: 365 testów jednostkowych
i regresyjnych oraz 8 scenariuszy smoke przeszło. Po usunięciu ostrzeżeń
o usuwanym backendzie powtórzono test UI i scenariusze zamykania.
Testy nie używają mikrofonu ani prawdziwych
urządzeń Smart Home. Fizycznego podłączenia ReSpeakera nie zweryfikowano
w środowisku wykonującym te testy.

## Test użytkownika na Raspberry Pi po wdrożeniu

1. Bez ReSpeakera sprawdź czarną ikonę i opis po dotknięciu.
2. Podłącz ReSpeaker Lite do Pi przez jego port USB XMOS, zgodnie z
   [dokumentacją urządzenia](https://github.com/respeaker/ReSpeaker_Lite/).
3. Po około 2 sekundach sprawdź turkusową ikonę. Nie trzeba odświeżać ani
   ponownie uruchamiać HomeHub.
4. Odłącz USB: ikona powinna wrócić do czarnej. Powtórz na innym porcie.
5. Sprawdź, czy pozostałe panele działają jak wcześniej i czy zamknięcie
   aplikacji nie powoduje jej samoczynnego uruchomienia.

Zgodnie z ustaleniem użytkownika każdy etap kończymy testami, scaleniem
na `main`, pushem i weryfikacją budowania/wdrożenia na Pi. Dalszy etap
rozpoczynamy po opinii użytkownika. Nagrywanie, STT, TTS i AI pozostają
poza zakresem tego etapu.
