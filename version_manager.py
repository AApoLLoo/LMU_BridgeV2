# LMU_Bridge/version_manager.py
"""
Gestionnaire de version unifié et fluide
Gère la vérification, la comparaison et la récupération des informations de version
"""

import logging
import os
import sys
import json
from typing import Optional, Tuple, Dict
from functools import lru_cache
from datetime import datetime, timedelta
from tls_config import bootstrap_tls_env

logger = logging.getLogger(__name__)


class VersionInfo:
    """Classe pour représenter et comparer les versions"""

    def __init__(self, version_str: str):
        """
        Initialise une version à partir d'une chaîne
        Formats supportés: "1.2.3", "1.2.3-dev", "v1.2.3"
        """
        self.original = version_str
        self.version_str = version_str.lstrip('v').split('-')[0]
        self.pre_release = '-' in version_str

        try:
            parts = [int(x) for x in self.version_str.split('.')]
            while len(parts) < 3:
                parts.append(0)
            self.major, self.minor, self.patch = parts[:3]
        except (ValueError, IndexError):
            logger.warning(f"Format de version invalide: {version_str}")
            self.major = self.minor = self.patch = 0

    @property
    def tuple(self) -> Tuple[int, int, int]:
        """Retourne la version sous forme de tuple (pour comparaison facile)"""
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"VersionInfo('{self.original}')"

    def __eq__(self, other) -> bool:
        if isinstance(other, VersionInfo):
            return self.tuple == other.tuple
        return str(self) == str(other)

    def __lt__(self, other) -> bool:
        if isinstance(other, VersionInfo):
            return self.tuple < other.tuple
        return self.tuple < VersionInfo(str(other)).tuple

    def __le__(self, other) -> bool:
        return self == other or self < other

    def __gt__(self, other) -> bool:
        if isinstance(other, VersionInfo):
            return self.tuple > other.tuple
        return self.tuple > VersionInfo(str(other)).tuple

    def __ge__(self, other) -> bool:
        return self == other or self > other

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class VersionManager:
    """Gestionnaire centralisé des versions"""

    # Configuration
    CACHE_DIR = os.path.expanduser("~/.lmu_bridge")
    CACHE_FILE = os.path.join(CACHE_DIR, "version_cache.json")
    CACHE_DURATION = timedelta(hours=24)  # Mettre en cache pendant 24h

    def __init__(self):
        """Initialise le gestionnaire de version"""
        self._ensure_cache_dir()
        self._current_version: Optional[VersionInfo] = None
        self._cache: Dict = self._load_cache()

    @staticmethod
    def _ensure_cache_dir():
        """Crée le répertoire de cache s'il n'existe pas"""
        os.makedirs(VersionManager.CACHE_DIR, exist_ok=True)

    def _load_cache(self) -> Dict:
        """Charge le cache depuis le fichier"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Impossible de charger le cache: {e}")
        return {}

    def _save_cache(self):
        """Sauvegarde le cache dans le fichier"""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder le cache: {e}")

    def _is_cache_valid(self, key: str) -> bool:
        """Vérifie si une entrée du cache est encore valide"""
        if key not in self._cache:
            return False

        try:
            cache_time = datetime.fromisoformat(self._cache[key].get('timestamp'))
            return datetime.now() - cache_time < self.CACHE_DURATION
        except (ValueError, KeyError, TypeError):
            return False

    def get_current_version(self) -> VersionInfo:
        """Récupère la version courante de l'application"""
        if self._current_version is None:
            try:
                from version import __version__
                self._current_version = VersionInfo(__version__)
            except ImportError:
                logger.error("Impossible de charger le module 'version'")
                self._current_version = VersionInfo("0.0.0")

        return self._current_version

    def get_python_version(self) -> str:
        """Récupère la version de Python"""
        return ".".join(map(str, sys.version_info[:3]))

    def format_version_info(self) -> str:
        """Retourne les informations de version formatées"""
        return f"LMU_Bridge {self.get_current_version()}"

    def is_newer_available(self, remote_version: str) -> bool:
        """Vérifie si une version remote est plus récente que la version actuelle"""
        current = self.get_current_version()
        remote = VersionInfo(remote_version)
        return remote > current

    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare deux versions
        Retourne:
            -1 si version1 < version2
             0 si version1 == version2
             1 si version1 > version2
        """
        v1 = VersionInfo(version1)
        v2 = VersionInfo(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0


class GitHubReleaseChecker:
    """Vérificateur de releases GitHub avec cache"""

    def __init__(self, repo: str, app_name: str = "LMU_Bridge"):
        """
        Initialise le vérificateur GitHub

        Args:
            repo: Format "owner/repo" (ex: "AApoLLoo/LMU_BridgeV2")
            app_name: Nom de l'application pour l'User-Agent
        """
        self.repo = repo
        self.app_name = app_name
        self.version_manager = VersionManager()
        self._api_url = f"https://api.github.com/repos/{repo}/releases"
        self._ca_bundle = bootstrap_tls_env()

    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requêtes GitHub"""
        current_version = self.version_manager.get_current_version()
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{self.app_name}/{current_version}"
        }

    def get_latest_release(self, use_cache: bool = True) -> Optional[Dict]:
        """
        Récupère les informations de la dernière release

        Args:
            use_cache: Si True, utilise le cache si disponible

        Returns:
            Dict avec "version", "url", "description" ou None en cas d'erreur
        """
        cache_key = f"github_release_{self.repo}"

        # Vérifier le cache
        if use_cache and self.version_manager._is_cache_valid(cache_key):
            logger.debug("Utilisation du cache pour la release GitHub")
            return self.version_manager._cache[cache_key].get('data')

        # Récupérer depuis l'API
        try:
            import requests
            response = requests.get(
                self._api_url,
                headers=self._get_headers(),
                verify=self._ca_bundle if self._ca_bundle else True,
                timeout=5
            )

            if response.status_code == 200:
                releases = response.json()

                if not releases:
                    logger.warning("Aucune release trouvée")
                    return None

                # Prendre la première release (plus récente)
                release_data = releases[0]
                return self._parse_release(release_data)

            elif response.status_code == 404:
                logger.error(f"Repository introuvable ou privé: {self.repo}")
                return None

            else:
                logger.error(f"Erreur API GitHub: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.warning("Timeout lors de la connexion à GitHub")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification GitHub: {e}")
            return None

    def _parse_release(self, release_data: Dict) -> Optional[Dict]:
        """Parse les données d'une release GitHub"""
        try:
            tag_name = release_data.get("tag_name", "").lstrip("v")
            release_notes = release_data.get("body", "")
            assets = release_data.get("assets", [])

            # Chercher le lien de téléchargement
            download_url = None
            for asset in assets:
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            result = {
                "version": tag_name,
                "url": download_url,
                "description": release_notes,
                "timestamp": datetime.now().isoformat()
            }

            # Sauvegarder dans le cache
            cache_key = f"github_release_{self.repo}"
            self.version_manager._cache[cache_key] = {"data": result, "timestamp": result["timestamp"]}
            self.version_manager._save_cache()

            return result

        except Exception as e:
            logger.error(f"Erreur lors du parsing de la release: {e}")
            return None

    def check_for_updates(self) -> Optional[Dict]:
        """
        Vérifie s'il y a une mise à jour disponible

        Returns:
            Dict avec "update_available", "current", "latest", "url" ou None en cas d'erreur
        """
        latest = self.get_latest_release()

        if not latest:
            return None

        current = self.version_manager.get_current_version()
        latest_version = VersionInfo(latest["version"])

        return {
            "update_available": latest_version > current,
            "current": str(current),
            "latest": latest["version"],
            "url": latest["url"],
            "description": latest["description"]
        }


# Instance globale (Singleton)
_version_manager: Optional[VersionManager] = None
_github_checker: Optional[GitHubReleaseChecker] = None


def get_version_manager() -> VersionManager:
    """Récupère ou crée l'instance globale du gestionnaire de version"""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


def get_github_checker(repo: str = "AApoLLoo/LMU_BridgeV2") -> GitHubReleaseChecker:
    """Récupère ou crée l'instance globale du vérificateur GitHub"""
    global _github_checker
    if _github_checker is None:
        _github_checker = GitHubReleaseChecker(repo)
    return _github_checker

