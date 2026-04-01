# LMU_Bridge/version_config.py
"""
Configuration centralisée du système de versioning
Permet de personnaliser le comportement sans modifier les modules
"""

from datetime import timedelta

# ============================================================================
# Configuration GitHub
# ============================================================================

# Repository GitHub
GITHUB_REPO = "AApoLLoo/LMU_BridgeV2"

# Nom de l'application (pour User-Agent)
APP_NAME = "LMU_Bridge"

# ============================================================================
# Configuration du Cache
# ============================================================================

# Durée du cache en heures
CACHE_DURATION = timedelta(hours=24)

# Dossier du cache (défaut: ~/.lmu_bridge/)
# Laisser None pour utiliser le chemin par défaut
CACHE_DIRECTORY = None

# Nom du fichier de cache
CACHE_FILENAME = "version_cache.json"

# ============================================================================
# Configuration des Mises à Jour
# ============================================================================

# Timeout pour les requêtes GitHub (secondes)
UPDATE_TIMEOUT = 30

# Nombre maximum de tentatives
MAX_UPDATE_RETRIES = 3

# Afficher les dialogues Windows (False pour mode headless)
SHOW_DIALOGS = True

# ============================================================================
# Configuration du Logging
# ============================================================================

# Niveau de log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = "INFO"

# Format des logs
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# Fonctions Helper
# ============================================================================

def get_cache_config():
    """Retourne la configuration du cache"""
    from version_manager import VersionManager

    if CACHE_DIRECTORY:
        VersionManager.CACHE_DIR = CACHE_DIRECTORY

    VersionManager.CACHE_DURATION = CACHE_DURATION

    return {
        "directory": VersionManager.CACHE_DIR,
        "file": VersionManager.CACHE_FILE,
        "duration": CACHE_DURATION.total_seconds()
    }


def get_github_config():
    """Retourne la configuration GitHub"""
    return {
        "repo": GITHUB_REPO,
        "app_name": APP_NAME,
        "timeout": UPDATE_TIMEOUT,
        "max_retries": MAX_UPDATE_RETRIES
    }


def configure_logging():
    """Configure le logging selon la configuration"""
    import logging

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT
    )


# ============================================================================
# Exemple de Personnalisation
# ============================================================================

def example_customize():
    """Exemple: Comment personnaliser la configuration"""

    # Modifier la durée du cache
    # version_config.CACHE_DURATION = timedelta(hours=12)

    # Utiliser un cache personnalisé
    # version_config.CACHE_DIRECTORY = "/custom/path"

    # Modifier le timeout
    # version_config.UPDATE_TIMEOUT = 60

    # Désactiver les dialogues (mode headless)
    # version_config.SHOW_DIALOGS = False

    pass

