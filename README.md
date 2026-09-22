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

  
Project In Progress... 

**Main Widnow:**
<img width="1199" height="717" alt="image" src="https://github.com/user-attachments/assets/781f5cf8-bc97-4be5-a25b-8237781b3214" />

**Popup for AC units:**
<img width="1275" height="711" alt="image" src="https://github.com/user-attachments/assets/fa893760-ef19-4e2c-ac99-6f0dacb7fad5" />

**Popup for Water Heater:**
<img width="1273" height="714" alt="image" src="https://github.com/user-attachments/assets/cf4fd5d7-e49e-4c54-a012-da29fad075c1" />




## Local verification

Use Python 3.11 or newer (the current pyairstage dependency uses `enum.StrEnum`).
Install `requirements.txt`, then run:

```sh
QT_QPA_PLATFORM=offscreen python -m pytest Tests/ --cov=App --cov=Adapters --cov=Ports --cov=Interface --cov-report=term-missing
```

Tests use fake device clients and do not control household devices. CI runs this
suite before the existing deployment job. Deployment still runs only on pushes
to main, on the Raspberry Pi self-hosted runner.

### Integration issues still requiring device verification

- Atlantic capability 157 describes a temporary temperature override; it does not
  establish electrical power or active heating. The existing power indicator is
  still a heuristic. Cancelling the override can resume the schedule rather than
  switch the heater off. Compare sanitized API snapshots in those states before
  implementing reliable power controls.
- Check boiler mode/temperature changes and readback on the actual device. The
  panel now sequences mode and temperature writes and reports refresh failures;
  a successful readback request alone does not guarantee the new settings have
  already propagated through the cloud.
- MQTT callbacks currently run on another thread; database recording needs an
  explicit handoff to the asyncio event loop. Missing sensor values also still
  default to zero and need a separate unavailable/stale state.
- Startup still depends on successful AC and boiler authentication. Device
  isolation, retry/backoff, and deployment rollback need further work.
- A credential was removed from the legacy boiler example. Rotate that credential;
  editing the file does not remove it from Git history.


## Demo on macOS

The demo opens in a regular 1200×800 window and uses in-memory devices: two ACs,
three heaters, an Ariston-like boiler, and fixed temperature/humidity readings.
Controls change only simulated settings; changes reset when the app restarts.
It does not load credentials or connect to cloud APIs, MQTT, BLE, or PostgreSQL.
This is an interface demo, not a simulation of heating physics or device protocols.
The Raspberry Pi entry point and CI deployment remain in live mode.

From the repository directory, using Python 3.11 or newer:

```sh
python3 -m venv .venv-demo
source .venv-demo/bin/activate
python -m pip install -r requirements-demo.txt
python run_demo.py
```

Close with the window close button or the app's × button.

After setup, you can also double-click `run-demo.command` in Finder.
