#!/bin/bash
# deploy_baza.sh – uruchamiany przez CI/CD na RPi5
# Umieść go w: /home/miggie/deploy_baza.sh
# Nadaj uprawnienia: chmod +x /home/miggie/deploy_baza.sh

set -e  # zatrzymaj na błędzie

DEPLOY_DIR="/home/miggie/Baza_Domowa"
ARCHIVE="/tmp/baza_domowa.tar.gz"
VENV_DIR="/home/miggie/.virtualenvs/Baza_Domowa"
SERVICE_NAME="bazadomowa"

echo "=== Deploy Baza Domowa ==="
echo "Czas: $(date)"

# 1. Zatrzymaj serwis (jeśli działa)
echo "[1/4] Zatrzymywanie serwisu..."
systemctl --user stop "$SERVICE_NAME" 2>/dev/null || echo "  Serwis nie był uruchomiony."

# 2. Rozpakuj archiwum
echo "[2/4] Rozpakowywanie archiwum..."
mkdir -p "$DEPLOY_DIR"
tar -xzf "$ARCHIVE" -C "$DEPLOY_DIR" --overwrite

# 3. Zaktualizuj zależności Python
echo "[3/4] Aktualizacja pakietów Python..."
"$VENV_DIR/bin/pip" install -r "$DEPLOY_DIR/requirements.txt" --quiet

# 4. Uruchom serwis
echo "[4/4] Uruchamianie serwisu..."
systemctl --user start "$SERVICE_NAME"
systemctl --user enable "$SERVICE_NAME"

echo ""
echo "=== Deploy zakończony pomyślnie! ==="
systemctl --user status "$SERVICE_NAME" --no-pager

