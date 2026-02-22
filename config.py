import os
from dotenv import load_dotenv
from pathlib import Path

# Charge les variables du fichier .env
load_dotenv()

# Vérification rapide
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("⚠️ ERREUR : La clé GEMINI_API_KEY est introuvable dans le fichier .env")

# Chemins des dossiers
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR / os.getenv("WORKSPACE_DIR", "workspace")

# Création du dossier workspace s'il n'existe pas
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)