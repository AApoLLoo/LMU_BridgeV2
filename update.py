# LMU_Bridge/update.py
"""
Module de compatibilité pour les mises à jour
Utilise le nouveau système de gestionnaire de mise à jour
"""

import logging
from update_manager import get_update_manager

logger = logging.getLogger(__name__)

# Configuration
REPO_NAME = "AApoLLoo/LMU_BridgeV2"
APP_NAME = "LMU_Bridge"


def get_latest_release_info():
    """
    Récupère la dernière release (compatibilité legacy)

    Returns:
        Tuple (version, download_url) ou (None, None) en cas d'erreur
    """
    manager = get_update_manager(REPO_NAME)
    release = manager.github_checker.get_latest_release()

    if not release:
        return None, None

    return release.get("version"), release.get("url")


def ask_user_confirmation(new_version):
    """Demande confirmation via popup"""
    manager = get_update_manager(REPO_NAME)
    update_info = {
        "current": str(manager.version_manager.get_current_version()),
        "latest": new_version
    }
    return manager.show_update_prompt(update_info)


def perform_update(download_url):
    """Effectue la mise à jour"""
    manager = get_update_manager(REPO_NAME)
    manager.perform_update(download_url)


def check_and_update():
    """
    Fonction principale pour vérifier et mettre à jour
    Utilise le nouveau système fluide
    """
    manager = get_update_manager(REPO_NAME)

    # Vérifier les mises à jour
    update_info = manager.github_checker.check_for_updates()

    if not update_info:
        logger.warning("Impossible de vérifier les mises à jour")
        return

    # Si une mise à jour est disponible
    if update_info.get("update_available"):
        if manager.show_update_prompt(update_info):
            download_url = update_info.get("url")
            if download_url:
                manager.perform_update(download_url)
            else:
                logger.error("URL de téléchargement introuvable")
    else:
        logger.info("Application à jour")
