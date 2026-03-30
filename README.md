**HomeHub App**

**HW**: Rasperry Pi 5, Raspberry Pi Touch Display 2 (7'')

**Frontend**: QML

**Backend**: Python, PyQT6

**Plan to integrate**:
- AC units (API connection, Control of temperature, Modes, reading the room temperature, working automation in summer/winter) ✔
- Electric heaters (API connection, Control of temperature, Modes, reading the room temperature, working automation in summer/winter) ✔ 
- Water Heater (API connection, Control of temperature, Modes, reading the room temperature, working automation in summer/winter) ✔
- Waher Machine (BLE connection, Check state of washing (on/off), check and display washing time) ✔
- Power consumption (API connection, get and save the data of hourly, daily, and monthly power consumption) ❌
- Weather station (Build and connect to small wather/garden station to read data from sensors(air pollution, humidity, temperature) ❌

**Further plans to develop**:
- Add tests (pytest)
- CI/CD (github actions)
- AI voice agent integration - controlling the APP through voice
- PostgreSQL database – saving sensor readings, weather data, power consumption ✔ (in progress)
- REST API (FastAPI) – external access to data ❌
- Web UI / PWA – mobile dashboard ❌

  
Project In Progress... 

**Main Widnow:**
<img width="1199" height="717" alt="image" src="https://github.com/user-attachments/assets/781f5cf8-bc97-4be5-a25b-8237781b3214" />

**Popup for AC units:**
<img width="1275" height="711" alt="image" src="https://github.com/user-attachments/assets/fa893760-ef19-4e2c-ac99-6f0dacb7fad5" />

**Popup for Water Heater:**
<img width="1273" height="714" alt="image" src="https://github.com/user-attachments/assets/cf4fd5d7-e49e-4c54-a012-da29fad075c1" />

---

## 🖥️ Setup na nowym laptopie (Windows + PyCharm)

### 1. Wymagania wstępne
- **Python 3.12** → https://www.python.org/downloads/ (zaznacz "Add to PATH")
- **Git** → https://git-scm.com/download/win
- **Docker Desktop** → https://www.docker.com/products/docker-desktop/ (potrzebny do PostgreSQL)
- **PyCharm** → https://www.jetbrains.com/pycharm/

### 2. Sklonuj projekt
```bash
git clone <twoj-repo-url> Baza_Domowa
cd Baza_Domowa
```

### 3. Utwórz i aktywuj virtualenv w PyCharm
Otwórz projekt w PyCharm → prawy dolny róg → interpreter → Add New → Virtualenv → Python 3.12.

Lub z terminala:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 4. Zainstaluj zależności
```bash
pip install -r requirements.txt
```

### 5. Skonfiguruj zmienne środowiskowe
```bash
# Skopiuj przykładowy plik
copy Config\.env.example Config\.env
```
Otwórz `Config/.env` i wpisz swoje dane (hasła, ID urządzeń).

### 6. Uruchom bazę danych PostgreSQL
```bash
# Upewnij się że Docker Desktop jest uruchomiony, potem:
docker compose up -d

# Sprawdź czy działa:
docker compose ps
```
Baza startuje automatycznie, tabele tworzą się same przy pierwszym uruchomieniu aplikacji.

### 7. Uruchom aplikację
```bash
python View/main.py
```
Lub w PyCharm: prawym na `View/main.py` → Run.

### 8. Konfiguracja PyCharm (opcjonalne ale wygodne)
- **Run configuration**: `View/main.py`, working directory = root projektu
- **Mark as Sources Root**: prawy na folder główny → Mark Directory as → Sources Root
- **Interpreter**: upewnij się że wskazuje na `.venv` z kroku 3

---

## 📁 Struktura projektu

```
Baza_Domowa/
├── Adapters/       # Implementacje portów (AC, grzejniki, czujniki, baza, pogoda)
├── App/            # Serwisy aplikacyjne (logika biznesowa)
├── Compositions/   # Dependency Injection – składanie całości
├── Config/
│   ├── settings.py     # Konfiguracja aplikacji
│   ├── .env            # Twoje hasła/klucze (NIE commituj!)
│   └── .env.example    # Szablon – skopiuj i uzupełnij
├── Interface/      # Qt backend (QObject/sygnały)
├── Ports/          # Interfejsy (Protocol) – kontrakt między warstwami
├── Tests/          # Testy pytest
├── View/           # Frontend QML
│   └── main.py         # ← punkt startowy aplikacji
├── docker-compose.yml  # PostgreSQL + Adminer
└── requirements.txt    # Zależności Python
```

## 🗄️ Baza danych – Adminer (UI)
Po uruchomieniu `docker compose up -d` dostępny pod `http://localhost:8081`:
- System: `PostgreSQL`
- Server: `postgres`
- Username: `baza`
- Password: `baza`
- Database: `baza_domowa`
