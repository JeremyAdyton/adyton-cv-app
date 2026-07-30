#!/bin/bash
# Script de build pour Render.com
# 1. Build du frontend React
# 2. Installation des dépendances Python
set -e

echo "📦 Build du frontend..."
cd frontend
npm install
npm run build
cd ..

echo "🐍 Installation des dépendances Python..."
pip install -r backend/requirements.txt

echo "✅ Build terminé !"
