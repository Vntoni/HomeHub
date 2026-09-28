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


## Raspberry Pi deployment session

The Actions runner runs as a system service, while `bazadomowa` is a user
service. Both must use the same Linux account (`miggie` in this installation).
The workflow sets `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` for that
account before invoking `systemctl --user`, and checks the bus and application
unit before building or replacing the installed application.

For deployments without an interactive login, run once on the Pi:

```sh
sudo loginctl enable-linger miggie
```

Then, in a terminal logged in as `miggie`, verify:

```sh
systemctl --user status bazadomowa
```

If the workflow reports that the user bus is unavailable, verify the user manager
with `systemctl status user@1000.service` (1000 is miggie's UID on this Pi).
The workflow never ignores errors stopping the application. Deployment jobs are
serialized, and startup is checked again after ten seconds; this checks process
availability, not device connectivity or successful display rendering.
### Touch panel UI verification

The touch panel uses compact, responsive cards and explicit **Ustawienia** buttons.
AC, boiler and heater settings use a shared temperature stepper and report the
result of each save. A successful command/readback does not guarantee immediate
cloud propagation. Heater switches describe a temporary temperature override,
not verified electrical power.

After installing the demo requirements and pytest dependencies:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python Tests/ui_smoke.py
```

Pass an optional output directory to save screenshots. This check uses demo
services with network access blocked, exercises settings and power controls,
checks failure feedback and washer states, and renders 1280×720, 800×480 and
720×1280 layouts. Small screens scroll the cards and the body of settings dialogs;
the apply and close buttons remain outside the scrolling form.


AC settings also expose **Cisza / Niska / Średnia / Wysoka / Auto** for indoor fan
speed, separately from the outdoor low-noise option. The adapter uses
`pyairstage.FanSpeed` through `set_fan_speed` (`iu_fan_spd`): QUIET=2, LOW=5,
MEDIUM=8, HIGH=11, AUTO=0. The form reads the existing fan level on open and
shows its readback after saving. Unchanged intermediate readings are preserved;
fan-only mode does not send a target-temperature command. Unit tests exercise
the real pyairstage encoding with a fake transport; live-device verification is
still required. Reference: [pyairstage fan constants](https://github.com/danielkaldheim/pyairstage/blob/master/pyairstage/constants.py).
