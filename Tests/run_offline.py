"""Run all tests and both existing QML smokes in separate offline processes.

Usage: python Tests/run_offline.py
       python Tests/run_offline.py --pytest-only Tests/Unit/test_washer_lifecycle.py
"""
import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def worker(stage, targets):
    if stage == "guard_smoke":
        # This separate self-test installs its own guard and expects violations.
        runpy.run_path(str(ROOT / "Tests" / "guard_smoke.py"), run_name="__main__")
        return 0
    from Tests.offline_guard import OfflineGuard
    guard = OfflineGuard()
    guard.install()  # Before pytest collection and application imports.
    result = 0
    try:
        if stage == "pytest":
            import pytest
            result = int(pytest.main([
                "-p", "pytest_asyncio.plugin", "-p", "pytest_cov.plugin",
                *(targets or ["Tests/"]), "--cov=App", "--cov=Adapters",
                "--cov=Ports", "--cov=Interface", "--cov-report=term-missing",
                "--cov-report=xml:test-results/coverage.xml",
                "--junitxml=test-results/pytest.xml",
            ]))
        else:
            sys.argv = [str(ROOT / "Tests" / f"{stage}.py")]
            runpy.run_path(sys.argv[0], run_name="__main__")
    finally:
        if guard.violations:
            print(f"Offline isolation failed: {guard.violations}", flush=True)
    # Swallowing a transport exception in application code cannot hide a breach.
    return 1 if guard.violations else result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=["guard_smoke", "pytest", "demo_smoke", "ui_smoke", "ac_power_smoke", "shutdown_smoke", "qml_failure_smoke"])
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--pytest-only", action="store_true")
    selection.add_argument("--smoke-only", nargs="+", choices=["demo_smoke", "ui_smoke", "ac_power_smoke", "shutdown_smoke", "qml_failure_smoke"])
    parser.add_argument("targets", nargs="*")
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker, args.targets)
    (ROOT / "test-results").mkdir(exist_ok=True)
    failed = False
    with tempfile.TemporaryDirectory(prefix="homehub-tests-") as isolated:
        # Allowlist: no cloud credentials, DB DSN, proxies or user Python plugins.
        env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "LANG")
               if key in os.environ}
        env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONNOUSERSITE="1",
                   COVERAGE_FILE=str(ROOT / "test-results" / ".coverage"),
                   XDG_CONFIG_HOME=isolated, XDG_CACHE_HOME=isolated,
                   TMPDIR=isolated, PYTHONUNBUFFERED="1")
        stages = ["guard_smoke", "pytest"] if args.pytest_only else ["guard_smoke", "pytest", "demo_smoke", "ui_smoke", "ac_power_smoke", "shutdown_smoke", "qml_failure_smoke"]
        if args.smoke_only:
            stages = ["guard_smoke", *args.smoke_only]
        for stage in stages:
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", stage]
            if stage == "pytest":
                command.extend(args.targets)
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, timeout=180,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                output, code = result.stdout, result.returncode
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout or b""
                if isinstance(output, bytes):
                    output = output.decode(errors="replace")
                output += "\nFAILED: process exceeded 180 seconds\n"
                code = 124
            (ROOT / "test-results" / f"{stage}.log").write_text(output, encoding="utf-8")
            print(output, end="", flush=True)
            print(f"{stage}: exit {code}", flush=True)
            if stage == "guard_smoke" and code != 0:
                return 1  # Do not run application tests with a broken guard.
            failed |= code != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
