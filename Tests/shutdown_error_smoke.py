"""Cleanup failures remain observable; other resources still close."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("shutdown_smoke.py")),
              init_globals={"FAIL_CLEANUP": True}, run_name="__main__")
