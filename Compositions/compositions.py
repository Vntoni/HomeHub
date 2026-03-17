# src/home/composition.py
import asyncio
import ariston
from pyairstage.airstageAC import AirstageAC, ApiCloud
from Model.Backend.washer_ble import WasherMachine
from Config.settings import get_settings
from Adapters.airstage_ac_adapter import AirstageACAdapter
from Adapters.ariston_boiler_adapter import AristonBoilerAdapter
from Adapters.washer_ble_adapter import WasherBleAdapter
from Adapters.postgres_repository_adapter import PostgresRepositoryAdapter
from Adapters.open_meteo_adapter import OpenMeteoAdapter
from App.climate_service import ClimateService
from App.water_heater_service import WaterHeaterService
from App.washer_service import WasherService
from Interface.qt_backend import QtHomeBackend

async def build_backend() -> QtHomeBackend:
    s = get_settings()

    # --- Baza danych PostgreSQL ---
    repo = None
    try:
        repo = PostgresRepositoryAdapter(dsn=s.db_dsn)
        await repo.connect()
        print("✓ Baza danych PostgreSQL połączona")
    except Exception as e:
        print(f"⚠ Baza danych niedostępna (dane nie będą zapisywane): {e}")
        repo = None

    # --- Airstage (klima) ---
    try:
        api = ApiCloud(username=s.user, password=s.pwd, country=s.airstage_country)
        await api.authenticate()
    except Exception as e:
        raise RuntimeError("Airstage API could not be initialized.")

    ac_salon = AirstageACAdapter(s.salon_id, api, AirstageAC)
    ac_jadalnia = AirstageACAdapter(s.jadalnia_id, api, AirstageAC)
    climate = ClimateService({"Salon": ac_salon, "Jadalnia": ac_jadalnia})

    # --- Ariston (bojler) ---
    boiler_client = None
    try:
        await ariston._async_connect(s.user, s.ariston_pwd)
        boiler_client = await ariston.async_hello(s.user, s.ariston_pwd, s.ariston_device_id,  True, "en-US")
    except Exception as e:
        print(f"Błąd logowania do Boilera API: {e}")
    if boiler_client is None:
        raise RuntimeError("Boiler client could not be initialized.")
    boiler = AristonBoilerAdapter(boiler_client)
    boiler_svc = WaterHeaterService(boiler)
    print("Boiler svc:", boiler_svc)

    # --- Pralka (BLE) ---
    washer_svc = None
    try:
        washer_adapter = WasherBleAdapter(WasherMachine())
        washer_svc = WasherService(washer_adapter, poll_seconds=s.washer_poll_seconds)
    except Exception as e:
        print(f"Błąd polaczenia do Pralki BLE: {e}")

    # --- Cozy Touch (grzejniki Atlantic) ---
    heater_svc = None
    if s.cozytouch_user and s.cozytouch_pwd:
        try:
            from atlantic_client import AtlanticCozytouchClient
            from Adapters.cozytouch_heater_adapter import CozyTouchHeaterAdapter
            from App.heater_service import HeaterService

            print("\n" + "="*60)
            print("INICJALIZACJA GRZEJNIKÓW ATLANTIC COZY TOUCH")
            print("="*60)

            # Inicjalizacja klienta Atlantic
            atlantic_client = AtlanticCozytouchClient(
                username=s.cozytouch_user,
                password=s.cozytouch_pwd,
                scope=s.cozytouch_scope
            )

            # Logowanie
            print("Logowanie do Atlantic API...")
            if not atlantic_client.login():
                raise RuntimeError("Failed to login to Atlantic API")
            print("✓ Zalogowano pomyślnie")

            # Pobierz urządzenia
            print("Pobieranie urządzeń...")
            devices = atlantic_client.get_devices()
            print(f"✓ Znaleziono {len(devices)} urządzeń")

            if not devices:
                print("⚠ No Cozy Touch heaters found")
            else:
                # Mapowanie device ID → nazwa pokoju
                # Capability 154 zawiera nazwę pokoju (ze sniffingu)
                heaters = {}

                for device in devices:
                    device_id = device.get('deviceId')
                    device_name = device.get('name', f'Heater_{device_id}')

                    # Znajdź nazwę pokoju z capability 154
                    room_name = None
                    for cap in device.get('capabilities', []):
                        if cap.get('capabilityId') == 154:
                            room_name = cap.get('value')
                            break

                    # Użyj nazwy pokoju lub nazwy urządzenia
                    heater_key = room_name if room_name else device_name

                    # Utwórz adapter
                    adapter = CozyTouchHeaterAdapter(atlantic_client, device_id)
                    heaters[heater_key] = adapter

                    # Pokaż dane tego grzejnika
                    print(f"\n  Grzejnik: {heater_key} (ID: {device_id})")
                    try:
                        current = adapter.get_current_temperature()
                        target = adapter.get_target_temperature()
                        mode = adapter.get_mode()
                        online = adapter.is_online()
                        print(f"    - Temp aktualna: {current}°C")
                        print(f"    - Temp docelowa: {target}°C")
                        print(f"    - Tryb: {mode}")
                        print(f"    - Online: {online}")
                    except Exception as e:
                        print(f"    ⚠ Błąd odczytu danych: {e}")

                if heaters:
                    heater_svc = HeaterService(heaters)
                    print(f"\n✓ Zainicjalizowano {len(heaters)} grzejników: {list(heaters.keys())}")
                    print("="*60 + "\n")
                else:
                    print("⚠ No heaters found in Cozy Touch account")

        except Exception as e:
            print(f"❌ Błąd inicjalizacji grzejników Cozy Touch: {e}")
            import traceback
            traceback.print_exc()

    # --- Sensory Zigbee (MQTT) ---
    sensor_svc = None
    try:
        from Adapters.zigbee_sensor_adapter import ZigbeeSensorAdapter
        from App.sensor_service import SensorService

        _backend_ref = [None]  # będzie wypełnione po utworzeniu backend

        # Lista pokoi z .env (SENSOR_ROOMS=salon,jadalnia)
        _sensor_rooms = [r.strip() for r in s.sensor_rooms.split(",") if r.strip()]

        def _make_sensor_update(backend_ref, room, svc_ref):
            def _on_update(name, data):
                # Emit do Qt UI
                if backend_ref[0]:
                    backend_ref[0].sensorTempChanged.emit(room, float(data.get("temperature", 0.0)))
                    backend_ref[0].sensorHumidityChanged.emit(room, float(data.get("humidity", 0.0)))
                # Zapis do bazy przez SensorService
                if svc_ref[0]:
                    svc_ref[0].record_reading(room, data)
            return _on_update

        _svc_ref = [None]  # forward reference na sensor_svc
        sensors_dict = {
            room: ZigbeeSensorAdapter(room, on_update=_make_sensor_update(_backend_ref, room, _svc_ref))
            for room in _sensor_rooms
        }
        sensor_svc = SensorService(sensors_dict, repository=repo)
        _svc_ref[0] = sensor_svc
        print(f"✓ Sensory Zigbee zainicjalizowane: {_sensor_rooms}")
    except Exception as e:
        print(f"Błąd inicjalizacji sensorów Zigbee: {e}")
        _backend_ref = [None]

    # --- Qt adapter (QObject) ---
    backend = QtHomeBackend(climate, boiler_svc, washer_svc, heater_svc, sensor_svc)
    _backend_ref[0] = backend  # teraz callback ma dostęp do backend

    # --- Pogoda Open-Meteo (polling w tle) ---
    if repo:
        weather_adapter = OpenMeteoAdapter(
            latitude=s.weather_latitude,
            longitude=s.weather_longitude,
            repository=repo,
            poll_interval_seconds=s.weather_poll_interval_seconds,
        )
        asyncio.create_task(weather_adapter.start_polling())
        print(f"✓ Polling pogody Open-Meteo uruchomiony (co {s.weather_poll_interval_seconds}s)")

    return backend
