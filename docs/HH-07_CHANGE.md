# HH-07 — zachowanie ostatnich danych po nieudanym odczycie

## Problem

Po błędzie odświeżenia backend zmieniał status dostępności, ale interfejs nie
rozróżniał braku nowego odczytu od aktualnych danych. Użytkownik mógł odczytać
pozostawioną wartość bez informacji, że pochodzi ona z wcześniejszego pomiaru.

## Zmiana

Backend utrzymuje stan świeżości per urządzenie (`ac`, `boiler`, `heater`) i
emituje `deviceStaleChanged`. Błąd odczytu oznacza dane jako nieaktualne, a
poprawny późniejszy odczyt usuwa oznaczenie. Ostatnie wartości pozostają w
pamięci i są nadal publikowane; nie są zastępowane zerem ani inną wartością
zastępczą.

Karty urządzeń pokazują komunikat „Dane nieaktualne — zachowano ostatni
odczyt”. Polecenia pozostają związane z istniejącym statusem dostępności i
koordynatorem operacji.

## Testy

Dodano regresje backendu dla oznaczenia bojlera po błędzie oraz wyczyszczenia
oznaczenia po poprawnym odczycie. Kod przechodzi kontrolę składni i `git diff
--check`. Uruchomienie testów wymagających Qt zostało zablokowane przez limit
środowiska wykonawczego (`requires neon` / automatyczna kontrola usage limit),
więc wynik tej części pozostaje do ponownego potwierdzenia.

Nie wykonywano połączeń z fizycznymi urządzeniami.
