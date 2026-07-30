# Déploiement sur Render.com — Guide pas à pas

Durée estimée : **15 minutes**
Résultat : une URL accessible à toute l'équipe, ex. `https://adyton-cv-app.onrender.com`

---

## Étape 1 — Créer un compte GitHub (gratuit)

GitHub est le service où on va stocker le code de l'application.

1. Aller sur **https://github.com**
2. Cliquer sur **"Sign up"**
3. Renseigner : email, mot de passe, nom d'utilisateur
4. Confirmer l'email reçu

---

## Étape 2 — Uploader le code sur GitHub

1. Sur GitHub, cliquer sur le bouton **"+"** en haut à droite → **"New repository"**
2. Nom du dépôt : `adyton-cv-app`
3. Laisser tout le reste par défaut, cliquer **"Create repository"**
4. Sur la page qui s'affiche, cliquer **"uploading an existing file"**
5. Glisser-déposer **tout le contenu du dossier `adyton-cv-app`** (pas le dossier lui-même, son contenu)
6. Cliquer **"Commit changes"**

> ⚠️ Il faut uploader les fichiers ET les sous-dossiers (backend/, frontend/).
> GitHub permet d'uploader des dossiers en les glissant directement.

---

## Étape 3 — Créer un compte Render (gratuit)

1. Aller sur **https://render.com**
2. Cliquer **"Get Started for Free"**
3. Choisir **"Continue with GitHub"** → autoriser l'accès
4. Vous êtes connecté avec votre compte GitHub

---

## Étape 4 — Créer le service web

1. Dans le dashboard Render, cliquer **"New +"** → **"Web Service"**
2. Sélectionner votre dépôt **`adyton-cv-app`** → cliquer **"Connect"**
3. Remplir les champs :

   | Champ | Valeur |
   |-------|--------|
   | Name | `adyton-cv-app` |
   | Region | Frankfurt (EU) |
   | Branch | `main` |
   | Runtime | **Python 3** |
   | Build Command | `./build.sh` |
   | Start Command | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |

4. Cliquer **"Create Web Service"**

---

## Étape 5 — Ajouter la clé API Anthropic

C'est la clé qui permet à l'application d'utiliser Claude pour analyser les CV.

1. Dans le dashboard du service, cliquer **"Environment"** (menu de gauche)
2. Cliquer **"Add Environment Variable"**
3. Renseigner :
   - **Key** : `ANTHROPIC_API_KEY`
   - **Value** : votre clé (`sk-ant-...`)
4. Cliquer **"Save Changes"**

L'application redémarre automatiquement.

---

## Étape 6 — Accéder à l'application

Après 2-3 minutes de déploiement (barre de progression verte), l'URL de votre application apparaît en haut du dashboard :

```
https://adyton-cv-app.onrender.com
```

Partagez cette URL à toute l'équipe — elle est accessible depuis n'importe où.

---

## Notes importantes

**Délai de démarrage (plan gratuit)**
Sur le plan gratuit, l'application se "met en veille" après 15 minutes sans utilisation.
Le premier accès après une période d'inactivité prend ~30 secondes.
Pour éviter ça : passer au plan "Starter" à $7/mois.

**Clé API Anthropic**
Chaque génération de template consomme environ **~0,01$** de crédit Anthropic (modèle Haiku).
Pour 100 CV générés par mois ≈ $1.

**Mise à jour du code**
Si on modifie l'application, il suffit de re-uploader les fichiers modifiés sur GitHub.
Render re-déploie automatiquement.
