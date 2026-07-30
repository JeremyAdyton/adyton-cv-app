#!/bin/bash
# start.sh — Lance le backend FastAPI et le frontend React
set -e

# ── Vérifications ────────────────────────────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "❌  ANTHROPIC_API_KEY non définie."
  echo "    Exportez-la avant de lancer : export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# ── Backend ──────────────────────────────────────────────────────────────────
echo "🔧  Installation des dépendances Python..."
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo "🚀  Démarrage du backend (http://localhost:8000)..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "🔧  Installation des dépendances Node..."
cd "$FRONTEND_DIR"
npm install --silent

echo "🚀  Démarrage du frontend (http://localhost:5173)..."
npm run dev &
FRONTEND_PID=$!

# ── Arrêt propre ─────────────────────────────────────────────────────────────
trap "echo ''; echo '⛔  Arrêt...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

echo ""
echo "✅  Application démarrée !"
echo "    → Frontend : http://localhost:5173"
echo "    → Backend  : http://localhost:8000"
echo ""
echo "    Ctrl+C pour arrêter."
wait
