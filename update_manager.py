# LMU_Bridge/update_manager.py
"""
Gestionnaire de mise à jour fluide et intuitif
"""

import logging
import os
import sys
import subprocess
import ctypes
import threading
from typing import Callable, Optional
from version_manager import get_github_checker, get_version_manager
from tls_config import bootstrap_tls_env

logger = logging.getLogger(__name__)


class UpdateManager:
    """Gestionnaire centralisé des mises à jour"""

    MAX_RETRIES = 3
    TIMEOUT = 30

    def __init__(self, repo: str = "AApoLLoo/LMU_BridgeV2"):
        """Initialise le gestionnaire de mise à jour"""
        self.repo = repo
        self.version_manager = get_version_manager()
        self.github_checker = get_github_checker(repo)
        self._is_updating = False
        self._ca_bundle = bootstrap_tls_env()

    def check_async(self, callback: Callable[[Optional[dict]], None]):
        """Vérifie les mises à jour de manière asynchrone"""
        def _check():
            try:
                result = self.github_checker.check_for_updates()
                callback(result)
            except Exception as e:
                logger.error(f"Erreur: {e}")
                callback(None)

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def show_update_prompt(self, update_info: dict) -> bool:
        """Affiche un dialogue de mise à jour"""
        current = update_info.get("current", "?")
        latest = update_info.get("latest", "?")

        message = (
            f"Mise à jour disponible !\n\n"
            f"Version actuelle : v{current}\n"
            f"Nouvelle version : v{latest}\n\n"
            f"Mettre à jour maintenant ?"
        )

        result = ctypes.windll.user32.MessageBoxW(
            0, message, "Mise à jour", 0x04 | 0x40 | 0x1000
        )
        return result == 6

    def perform_update(self, download_url: str) -> bool:
        """Exécute la mise à jour"""
        if not getattr(sys, 'frozen', False):
            logger.error("Mode script: .exe requis")
            return False

        self._is_updating = True
        try:
            return self._download_and_update(download_url)
        finally:
            self._is_updating = False

    def _download_and_update(self, url: str) -> bool:
        """Effectue le téléchargement"""
        import requests

        exe = sys.executable
        backup = exe + ".backup"

        try:
            # Backup
            if os.path.exists(exe):
                os.rename(exe, backup)

            # Téléchargement
            response = requests.get(
                url,
                stream=True,
                verify=self._ca_bundle if self._ca_bundle else True,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()

            with open(exe, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Redémarrage
            subprocess.Popen([exe] + sys.argv[1:])
            sys.exit(0)
            return True

        except Exception as e:
            logger.error(f"Erreur: {e}")
            if os.path.exists(backup):
                os.rename(backup, exe)
            return False


_update_manager: Optional[UpdateManager] = None

def get_update_manager(repo: str = "AApoLLoo/LMU_BridgeV2") -> UpdateManager:
    """Récupère le gestionnaire de mise à jour"""
    global _update_manager
    if _update_manager is None:
        _update_manager = UpdateManager(repo)
    return _update_manager

