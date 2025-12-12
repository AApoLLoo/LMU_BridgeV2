# LMU_Bridge/update.py
import requests
import logging
import os
import sys
import subprocess
import ctypes
from version import __version__ as CURRENT_VERSION

# --- CONFIGURATION ---
# Remplacez par votre repo: "Utilisateur/NomDuRepo"
REPO_NAME = "AApoLLoo/LMU_BridgeV2"
APP_NAME = "LMU_Bridge"

logger = logging.getLogger(__name__)


def get_latest_release_info():
    """
    Récupère la dernière release (même si c'est une Pre-release).
    """
    # MODIFICATION : On enlève "/latest" pour avoir la liste complète
    url = f"https://api.github.com/repos/{REPO_NAME}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{CURRENT_VERSION}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            releases = response.json()

            # Si la liste est vide
            if not releases:
                return None, None

            # On prend le premier élément de la liste (le plus récent)
            data = releases[0]

            tag_name = data.get("tag_name", "").lstrip("v")

            # Récupérer l'URL de l'asset (l'exe)
            assets = data.get("assets", [])
            download_url = None
            for asset in assets:
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            return tag_name, download_url

        elif response.status_code == 404:
            logger.error("Erreur 404: Repo introuvable ou Privé.")
            return None, None

    except Exception as e:
        logger.error(f"Erreur update check: {e}")

    return None, None


def ask_user_confirmation(new_version):
    """Demande à l'utilisateur s'il veut mettre à jour via une popup."""
    style = 0x04 | 0x40 | 0x1000  # Oui/Non + Info + TopMost
    title = "Mise à jour disponible"
    message = (f"Une nouvelle version v{new_version} est disponible.\n"
               f"Version actuelle : v{CURRENT_VERSION}\n\n"
               "Voulez-vous la télécharger et l'installer maintenant ?")

    # 6 = Oui, 7 = Non
    return ctypes.windll.user32.MessageBoxW(0, message, title, style) == 6


def perform_update(download_url):
    """Télécharge la mise à jour et remplace l'exécutable."""
    if getattr(sys, 'frozen', False):
        current_exe = sys.executable
    else:
        logger.warning("Mode script : mise à jour impossible (il faut être compilé en .exe)")
        return

    exe_dir = os.path.dirname(current_exe)
    exe_name = os.path.basename(current_exe)
    old_exe = os.path.join(exe_dir, f"{exe_name}.old")

    print(f"Téléchargement de {download_url}...")

    try:
        # 1. Nettoyage préventif
        if os.path.exists(old_exe):
            try:
                os.remove(old_exe)
            except:
                pass

        # 2. Renommage (Le "Trick" Windows)
        os.rename(current_exe, old_exe)

        # 3. Téléchargement
        response = requests.get(download_url, stream=True)
        with open(current_exe, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print("Mise à jour téléchargée. Redémarrage...")

        # 4. Redémarrage
        subprocess.Popen([current_exe] + sys.argv[1:])
        sys.exit(0)

    except Exception as e:
        logger.error(f"Erreur critique MAJ: {e}")
        print(f"Erreur: {e}")
        # Tentative de rollback
        if os.path.exists(old_exe) and not os.path.exists(current_exe):
            os.rename(old_exe, current_exe)


def check_and_update():
    """Fonction principale de DEBUG."""
    # Nettoyage
    if getattr(sys, 'frozen', False):
        old_exe = sys.executable + ".old"
        if os.path.exists(old_exe):
            try:
                os.remove(old_exe)
            except:
                pass

    # DEBUG: On affiche ce qu'on cherche
    ctypes.windll.user32.MessageBoxW(0, f"Je cherche une maj pour : {REPO_NAME}\nMa version : {CURRENT_VERSION}",
                                     "Debug Start", 0)

    try:
        latest_version, download_url = get_latest_release_info()
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0, f"Erreur API GitHub : {e}", "Erreur", 0x10)
        return

    # DEBUG: On affiche ce qu'on a trouvé
    if latest_version is None:
        ctypes.windll.user32.MessageBoxW(0, "Impossible de récupérer les infos GitHub (Repo introuvable ?)", "Erreur",
                                         0x10)
        return

    msg = f"Dernière version trouvée : {latest_version}\nURL : {download_url}"
    ctypes.windll.user32.MessageBoxW(0, msg, "Résultat GitHub", 0)

    if latest_version != CURRENT_VERSION:
        if download_url:
            if ask_user_confirmation(latest_version):
                perform_update(download_url)
        else:
            ctypes.windll.user32.MessageBoxW(0,
                                             "Nouvelle version détectée, mais AUCUN fichier .exe trouvé dans la release !",
                                             "Erreur Asset", 0x10)
    else:
        ctypes.windll.user32.MessageBoxW(0, "Aucune mise à jour nécessaire (Versions identiques).", "Info", 0)

    print(f"Vérification des mises à jour... (v{CURRENT_VERSION})")
    latest_version, download_url = get_latest_release_info()

    if latest_version and latest_version != CURRENT_VERSION:
        if download_url:
            if ask_user_confirmation(latest_version):
                perform_update(download_url)
            else:
                print("Mise à jour ignorée par l'utilisateur.")
        else:
            print(f"Nouvelle version v{latest_version} détectée, mais aucun .exe trouvé dans la release GitHub.")
    else:
        print("Application à jour.")