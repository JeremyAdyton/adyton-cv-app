# Adyton CV Template Generator — Guide de lancement

## Prérequis

- Python 3.10+
- Node.js 18+
- Une clé API Anthropic (`sk-ant-...`)

## Lancement en une commande

```bash
# 1. Définir la clé API
export ANTHROPIC_API_KEY=sk-ant-VOTRE_CLE_ICI

# 2. Lancer l'application
cd adyton-cv-app
chmod +x start.sh
./start.sh
```

L'application est accessible sur **http://localhost:5173**

---

## Lancement manuel (si start.sh ne fonctionne pas)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --reload --port 8000
```

### Frontend (dans un second terminal)

```bash
cd frontend
npm install
npm run dev
```

Ouvrir **http://localhost:5173**

---

## Structure du projet

```
adyton-cv-app/
├── backend/
│   ├── main.py              ← API FastAPI (endpoint /api/generate)
│   ├── extract_cv.py        ← Extraction texte PDF/DOCX
│   ├── generate_template.py ← Génération DOCX depuis JSON
│   ├── requirements.txt
│   └── assets/
│       └── Template_Adyton_BASE.docx
├── frontend/
│   ├── src/
│   │   ├── App.jsx          ← Interface React
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js       ← Proxy /api → localhost:8000
├── start.sh                 ← Script de lancement tout-en-un
└── LANCEMENT.md
```

## Flux de fonctionnement

1. L'utilisateur uploade un CV (PDF ou DOCX)
2. Le backend extrait le texte brut
3. Claude (claude-haiku) analyse le CV et structure les données en JSON
4. Le script génère le DOCX depuis `Template_Adyton_BASE.docx`
5. Le fichier est téléchargeable directement (`Template_Adyton_Conseil_Prénom_NOM_AAAA_MM_JJ.docx`)

## Mise à jour du template BASE

Pour mettre à jour le template de base, remplacer :
```
backend/assets/Template_Adyton_BASE.docx
```
