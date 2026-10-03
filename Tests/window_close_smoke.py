"""Window manager close must await async cleanup before leaving Qt."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("shutdown_smoke.py")),
              init_globals={"TRIGGER": "window"}, run_name="__main__")
