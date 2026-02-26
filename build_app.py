# Build script dla Baza_Domowa
# Kompiluje aplikację do standalone executable

import PyInstaller.__main__
import sys
from pathlib import Path

# Ścieżki
project_root = Path(__file__).parent
view_dir = project_root / "View"
qml_dir = view_dir / "Example"

print("=" * 60)
print("BUILDING BAZA_DOMOWA")
print("=" * 60)

# Separator ścieżek: ":" na Linux/Mac, ";" na Windows
sep = ";" if sys.platform == "win32" else ":"

# Parametry PyInstaller
args = [
    str(view_dir / "main.py"),  # Główny plik

    # Nazwa
    "--name=BazaDomowa",

    # Tryb: onedir jest bardziej niezawodny z PySide6 niż onefile
    # onefile rozpakowuje się do /tmp przy każdym starcie co może powodować problemy
    "--onedir",

    # Zbierz wszystkie pliki PySide6 (pluginy Qt, biblioteki, QML)
    "--collect-all=PySide6",
    "--collect-all=qasync",

    # Dane
    f"--add-data={qml_dir}{sep}View/Example",    # QML files
    f"--add-data={view_dir / 'images'}{sep}View/images",  # Images

    # Ukryte importy
    "--hidden-import=PySide6",
    "--hidden-import=PySide6.QtCore",
    "--hidden-import=PySide6.QtGui",
    "--hidden-import=PySide6.QtQml",
    "--hidden-import=PySide6.QtQuick",
    "--hidden-import=PySide6.QtQuickControls2",
    "--hidden-import=qasync",
    "--hidden-import=pyairstage",
    "--hidden-import=ariston",
    "--hidden-import=requests",
    "--hidden-import=cozypy",

    # Output
    "--distpath=dist",
    "--workpath=build",
    "--specpath=build",

    # Czyszczenie
    "--clean",
]

print("\nParametry PyInstaller:")
for arg in args:
    print(f"  {arg}")

print("\n" + "=" * 60)
print("Budowanie...")
print("=" * 60 + "\n")

try:
    PyInstaller.__main__.run(args)
    print("\n" + "=" * 60)
    print("✓ SUKCES!")
    print("=" * 60)
    print(f"\nPlik wykonywalny: dist/BazaDomowa.exe")
    print("\nUruchom: dist\\BazaDomowa.exe")
except Exception as e:
    print(f"\n✗ BŁĄD: {e}")
    sys.exit(1)
