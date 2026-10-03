"""Exercise Qt.quit(), used by the main window's close button."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("shutdown_smoke.py")),
              init_globals={"TRIGGER": "qml"}, run_name="__main__")
