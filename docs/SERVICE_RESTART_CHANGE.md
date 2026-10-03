# Wyłączenie automatycznego restartu

Na prośbę użytkownika usługa otrzymuje Restart=no zarówno w szablonie,
jak i w drop-in zapisywanym przez deploy na istniejącym Pi. Samo poprawienie
szablonu nie zmieniłoby już zainstalowanej usługi.

Log użytkownika wykazał RuntimeError: Event loop stopped before Future completed
podczas zamykania. Dotychczasowe Restart=on-failure / RestartSec=10 powodowało
ponowne otwarcie okna po takim wyjściu. Zmiana polityki wyłącza restart także
po innych awariach; jest to świadomie wybrany przez użytkownika prosty wariant.
Nie naprawia samego błędu zamykania pętli, który pozostaje osobnym problemem.

Nie zmieniono autostartu przy uruchomieniu systemu. Deploy nadal jawnie startuje
aplikację po podmianie. Ręczny start: systemctl --user start bazadomowa.
Kontrola ustawienia na Pi: systemctl --user show bazadomowa -p Restart.

MQTT: inicjalizacja lazienka jest potwierdzona logiem. Nasłuch mosquitto_sub
na localhost:1883 / zigbee2mqtt/czujnik_lazienka nie otrzymał wiadomości przez
60 sekund. Aktualnej publikacji czujnika, konfiguracji brokera Zigbee2MQTT
ani połączenia klienta HomeHub nie potwierdzono; brak podstaw do zmiany
transportu lub adresu brokera bez dalszej diagnostyki.
