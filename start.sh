#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "╔══════════════════════════════════════════╗"
echo "║    Amazon Invoice Analyzer — Démarrage   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Backend ───────────────────────────────────────────────────────────────────
echo "▶ Installation des dépendances Python…"
cd "$ROOT/backend"

# Prefer python3 / pip3
PYTHON=${PYTHON:-python3}
PIP=${PIP:-pip3}

$PIP install -r requirements.txt -q
$PYTHON -m playwright install chromium --with-deps 2>/dev/null || $PYTHON -m playwright install chromium

echo "▶ Démarrage du backend (port 8000)…"
$PYTHON -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────────────
echo "▶ Installation des dépendances Node…"
cd "$ROOT/frontend"
npm install --silent

echo "▶ Démarrage du frontend (port 5173)…"
npm run dev &
FRONTEND_PID=$!

# ── Open browser ──────────────────────────────────────────────────────────────
sleep 3
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  ✅  Application prête !                 ║"
echo "║  → http://localhost:5173                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Appuyez sur Ctrl+C pour arrêter."
echo ""

# Open in default browser (macOS / Linux)
if command -v open &>/dev/null; then
    sleep 1 && open http://localhost:5173
elif command -v xdg-open &>/dev/null; then
    sleep 1 && xdg-open http://localhost:5173
fi

trap "echo ''; echo 'Arrêt…'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
