"""Read-only checks for required files, Python syntax and tracked secrets."""
import ast
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    for filename in ("pytest.ini", "requirements.txt", "requirements-demo.txt",
                     "View/Example/main.qml", "View/Example/qmldir",
                     "View/images/images.py", "Tests/ui_smoke.py", "Tests/demo_smoke.py"):
        if not (ROOT / filename).is_file():
            raise RuntimeError(f"Missing project file: {filename}")
    directories = ("App", "Adapters", "Ports", "Interface", "Compositions", "Config", "Model", "View", "Tests")
    for directory in directories:
        for filename in (ROOT / directory).rglob("*.py"):
            ast.parse(filename.read_bytes(), filename=str(filename))
    for filename in ("atlantic_client.py", "mqtt_client.py", "build_app.py", "run_demo.py"):
        ast.parse((ROOT / filename).read_bytes(), filename=filename)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for filename in filter(None, tracked):
        name = Path(filename).name
        if name == ".env" or name.endswith(".token") or name == "token.json":
            raise RuntimeError("A credential file is tracked; review without printing its contents")
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    print("Project integrity and Python syntax passed (no application imports)")


if __name__ == "__main__":
    main()
