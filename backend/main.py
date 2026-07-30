"""
main.py — Backend FastAPI Adyton CV Template Generator
Lancement : uvicorn main:app --reload --port 8000
"""

import json
import os
import re
from datetime import date
from pathlib import Path

import anthropic
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from extract_cv import extract_text
from generate_template import generate

app = FastAPI(title="Adyton CV Template Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

EXTRACTION_PROMPT = """Tu es un assistant spécialisé dans l'extraction et la mise en forme de CV de consultants IT.

Analyse le CV ci-dessous et retourne UNIQUEMENT un objet JSON valide (sans texte avant ou après, sans balises markdown) avec cette structure exacte :

{
  "nom": "NOM Prénom  (majuscules pour le nom de famille, ex: DUPONT Thomas)",
  "titre": "Intitulé de poste synthétique, 5-8 mots max",
  "profil": [
    "Paragraphe 1 : identité + années d'expérience + spécialisation + secteurs clés (1 phrase dense)",
    "Paragraphe 2 : maîtrise des outils/solutions clés, exemples entre parenthèses (1 phrase)",
    "Paragraphe 3 : expérience opérationnelle concrète + certifications marquantes (1-2 phrases)",
    "Paragraphe 4 (optionnel, laisser '' si non pertinent) : langues"
  ],
  "competences": [
    {"categorie": "Catégorie courte", "contenu": "outil1, outil2, outil3"},
    ...
  ],
  "formation": [
    "Diplôme — École — Année",
    ...
  ],
  "missions": [
    {
      "company": "NOM CLIENT EN MAJUSCULES",
      "date": "AAAA – AAAA",
      "role": "Titre du poste",
      "bullets": [
        "Réalisation concrète commençant par un verbe d'action",
        ...
      ],
      "contexte": "outil1, outil2, outil3"
    }
  ]
}

Règles importantes :
- Le profil doit être COURT et DENSE au global (~80-100 mots maximum pour l'ensemble), réparti sur
  3 à 4 paragraphes COURTS (1 à 2 phrases chacun) — JAMAIS de longs paragraphes de 3+ phrases.
  Structure attendue :
    1. Identité + nombre d'années d'expérience + spécialisation + secteurs/contextes clés (1 phrase)
    2. Maîtrise des outils/solutions techniques clés, exemples entre parenthèses (1 phrase)
    3. Expérience opérationnelle concrète (niveaux, méthodologies) + certifications marquantes (1-2 phrases)
    4. Langues, uniquement si pertinent — sinon laisser une chaîne vide "" pour ce 4e paragraphe
  Un profil rédigé en 4 longs paragraphes détaillés est INCORRECT : viser la concision avant tout.
- Les compétences : 7 entrées maximum, contenu séparé par des virgules (jamais de puces)
- Les missions en ordre chronologique INVERSE (plus récente en premier)
- Les bullets : 3-6 par mission, commençant par un verbe d'action (Conception, Déploiement, Animation, etc.)
- La date : format "AAAA – AAAA" ou "AAAA – Actuel"
- Le company : TOUJOURS en MAJUSCULES

CV à analyser :
---
{cv_text}
---

JSON :"""


def build_filename(nom: str) -> str:
    """Construit le nom de fichier au format Adyton."""
    parts = nom.strip().split()
    if len(parts) >= 2:
        # Format stocké : "NOM Prénom" → fichier : "Prénom_NOM"
        # Si le premier token est en majuscules, c'est le nom de famille
        if parts[0] == parts[0].upper():
            prenom = "_".join(parts[1:])
            nom_fam = parts[0]
        else:
            prenom = parts[0]
            nom_fam = "_".join(parts[1:]).upper()
    else:
        prenom = nom
        nom_fam = ""

    today = date.today().strftime("%Y_%m_%d")
    return f"Template_Adyton_Conseil_{prenom}_{nom_fam}_{today}.docx"


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/generate")
async def generate_template(file: UploadFile = File(...)):
    # ── 1. Validation du fichier ──────────────────────────────────────────────
    allowed = {".pdf", ".docx", ".doc"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(400, f"Format non supporté : {ext}. Acceptés : PDF, DOCX")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Fichier trop volumineux (max 10 Mo)")

    # ── 2. Extraction du texte ────────────────────────────────────────────────
    try:
        cv_text = extract_text(content, file.filename)
    except Exception as e:
        raise HTTPException(422, f"Impossible de lire le fichier : {e}")

    if len(cv_text.strip()) < 100:
        raise HTTPException(422, "Le fichier semble vide ou illisible")

    # ── 3. Extraction structurée via Claude ───────────────────────────────────
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY non configurée")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.replace("{cv_text}", cv_text[:12000])
            }]
        )
        raw = message.content[0].text.strip()
    except anthropic.APIError as e:
        raise HTTPException(502, f"Erreur API Anthropic : {e}")

    # ── 4. Parse JSON ─────────────────────────────────────────────────────────
    # Nettoyer les éventuelles balises markdown
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        cv_data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(422, f"Réponse Claude invalide (JSON malformé) : {e}")

    # Validation minimale
    required_keys = {"nom", "titre", "profil", "competences", "formation", "missions"}
    missing = required_keys - set(cv_data.keys())
    if missing:
        raise HTTPException(422, f"Données manquantes dans l'extraction : {missing}")

    # ── 5. Génération DOCX ────────────────────────────────────────────────────
    try:
        docx_bytes = generate(cv_data)
    except ValueError as e:
        raise HTTPException(422, f"Erreur de génération : {e}")
    except Exception as e:
        raise HTTPException(500, f"Erreur interne : {e}")

    # ── 6. Retour du fichier ──────────────────────────────────────────────────
    filename = build_filename(cv_data.get("nom", "Consultant"))

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Filename": filename,
        }
    )


# ── Servir le frontend React (production) ────────────────────────────────────
# Le dossier dist/ est créé par "npm run build" dans frontend/
_static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")

