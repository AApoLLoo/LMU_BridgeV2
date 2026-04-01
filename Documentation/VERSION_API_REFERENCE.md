# VERSION SYSTEM - API REFERENCE

## 🔍 Vue d'Ensemble

```
version_manager.py
├── VersionInfo          (Représentation et comparaison)
├── VersionManager       (Gestion centrale)
├── GitHubReleaseChecker (Détection des releases)
└── Functions singletons (Accès facile)

update_manager.py
├── UpdateManager        (Gestion des mises à jour)
└── Function singleton   (Accès facile)

update.py               (Compatibilité legacy)
```

## 📚 VersionInfo

Représente une version SemVer avec support des opérateurs.

### Constructeur

```python
VersionInfo(version_str: str)
```

**Formats supportés:**
- `"1.2.3"` - Version standard
- `"1.2.3-dev"` - Version prérelease
- `"v1.2.3"` - Avec préfixe `v`

**Exemple:**
```python
v = VersionInfo("1.2.3")
v = VersionInfo("v1.2.3-beta")
```

### Propriétés

| Propriété | Type | Description |
|-----------|------|-------------|
| `major` | int | Numéro majeur |
| `minor` | int | Numéro mineur |
| `patch` | int | Numéro de patch |
| `original` | str | Version originale |
| `pre_release` | bool | Est une prérelease? |
| `tuple` | Tuple[int, int, int] | Tuple comparaison |

**Exemple:**
```python
v = VersionInfo("1.2.3")
print(v.major)   # 1
print(v.minor)   # 2
print(v.patch)   # 3
print(v.tuple)   # (1, 2, 3)
```

### Méthodes

| Méthode | Retour | Description |
|---------|--------|-------------|
| `__str__()` | str | Retourne "1.2.3" |
| `__repr__()` | str | Retourne "VersionInfo('...')" |
| `__eq__(other)` | bool | Égal? |
| `__lt__(other)` | bool | Inférieur? |
| `__le__(other)` | bool | Inférieur ou égal? |
| `__gt__(other)` | bool | Supérieur? |
| `__ge__(other)` | bool | Supérieur ou égal? |
| `__ne__(other)` | bool | Différent? |

**Exemple:**
```python
v1 = VersionInfo("1.0.0")
v2 = VersionInfo("1.0.1")

print(v1 < v2)    # True
print(v2 > v1)    # True
print(v1 == v1)   # True
print(v1 != v2)   # True
```

## 🎛️ VersionManager

Gestionnaire central des versions.

### Constructeur

```python
VersionManager()
```

### Propriétés

| Propriété | Type | Description |
|-----------|------|-------------|
| `CACHE_DIR` | str | Dossier du cache |
| `CACHE_FILE` | str | Chemin complet du cache |
| `CACHE_DURATION` | timedelta | Durée du cache |

### Méthodes

#### `get_current_version() -> VersionInfo`

Récupère la version courante.

```python
vm = get_version_manager()
version = vm.get_current_version()
print(version)  # "0.6.0"
```

#### `get_python_version() -> str`

Récupère la version de Python.

```python
version = vm.get_python_version()
print(version)  # "3.11.5"
```

#### `format_version_info() -> str`

Retourne les infos de version formatées.

```python
info = vm.format_version_info()
print(info)  # "LMU_Bridge 0.6.0"
```

#### `is_newer_available(remote_version: str) -> bool`

Vérifie si une version est plus récente.

```python
if vm.is_newer_available("1.0.0"):
    print("Mise à jour disponible")
```

#### `compare_versions(version1: str, version2: str) -> int`

Compare deux versions.

**Retours:**
- `-1` si version1 < version2
- `0` si version1 == version2
- `1` si version1 > version2

```python
result = vm.compare_versions("1.0.0", "1.0.1")
# -1 (1.0.0 est plus ancien)
```

## 🔗 GitHubReleaseChecker

Vérifie les releases sur GitHub.

### Constructeur

```python
GitHubReleaseChecker(repo: str, app_name: str = "LMU_Bridge")
```

**Paramètres:**
- `repo` - Format "owner/repo" (ex: "AApoLLoo/LMU_BridgeV2")
- `app_name` - Nom pour l'User-Agent

**Exemple:**
```python
checker = GitHubReleaseChecker("AApoLLoo/LMU_BridgeV2")
```

### Méthodes

#### `get_latest_release(use_cache: bool = True) -> Optional[Dict]`

Récupère la dernière release.

**Paramètres:**
- `use_cache` - Utiliser le cache? (défaut: True)

**Retour (Dict):**
```python
{
    "version": "1.0.0",
    "url": "https://...",
    "description": "Notes de release",
    "timestamp": "2026-04-01T12:00:00"
}
```

**Exemple:**
```python
release = checker.get_latest_release()
if release:
    print(f"Version: {release['version']}")
    print(f"URL: {release['url']}")
```

#### `check_for_updates() -> Optional[Dict]`

Vérifie s'il y a une mise à jour disponible.

**Retour (Dict):**
```python
{
    "update_available": True,
    "current": "0.6.0",
    "latest": "1.0.0",
    "url": "https://...",
    "description": "Notes de release"
}
```

**Exemple:**
```python
info = checker.check_for_updates()
if info and info["update_available"]:
    print(f"Version {info['latest']} disponible")
```

## 📦 UpdateManager

Gère les mises à jour.

### Constructeur

```python
UpdateManager(repo: str = "AApoLLoo/LMU_BridgeV2")
```

### Propriétés

| Propriété | Type | Description |
|-----------|------|-------------|
| `MAX_RETRIES` | int | Max tentatives (3) |
| `TIMEOUT` | int | Timeout en secondes (30) |

### Méthodes

#### `check_async(callback: Callable[[Optional[dict]], None])`

Vérifier asynchronement.

```python
def on_complete(info):
    print(f"Update available: {info['update_available']}")

um = get_update_manager()
um.check_async(on_complete)
```

#### `show_update_prompt(update_info: dict) -> bool`

Affiche un dialogue de mise à jour.

**Retour:**
- `True` si l'utilisateur accepte
- `False` sinon

```python
if um.show_update_prompt(info):
    um.perform_update(info["url"])
```

#### `perform_update(download_url: str) -> bool`

Exécute la mise à jour.

```python
success = um.perform_update("https://...")
if not success:
    print("Erreur lors de la mise à jour")
```

## 🔧 Fonctions Singletons

### `get_version_manager() -> VersionManager`

Récupère ou crée l'instance globale.

```python
from version_manager import get_version_manager

vm = get_version_manager()
```

### `get_github_checker(repo: str = "...") -> GitHubReleaseChecker`

Récupère ou crée le vérificateur GitHub.

```python
from version_manager import get_github_checker

checker = get_github_checker("AApoLLoo/LMU_BridgeV2")
```

### `get_update_manager(repo: str = "...") -> UpdateManager`

Récupère ou crée le gestionnaire de mise à jour.

```python
from update_manager import get_update_manager

um = get_update_manager()
```

## 📝 Update.py (Compatibilité)

### Fonctions

#### `get_latest_release_info() -> Tuple[str, str]`

Retourne (version, download_url) ou (None, None).

```python
from update import get_latest_release_info

version, url = get_latest_release_info()
```

#### `ask_user_confirmation(new_version: str) -> bool`

Affiche un dialogue de confirmation.

```python
from update import ask_user_confirmation

if ask_user_confirmation("1.0.0"):
    print("Utilisateur a accepté")
```

#### `perform_update(download_url: str)`

Effectue la mise à jour.

```python
from update import perform_update

perform_update("https://...")
```

#### `check_and_update()`

Vérifie et met à jour (fonction complète).

```python
from update import check_and_update

check_and_update()
```

## 🔄 Cache

### Fichier

Stocké dans `~/.lmu_bridge/version_cache.json`

```json
{
  "github_release_AApoLLoo/LMU_BridgeV2": {
    "data": {
      "version": "1.0.0",
      "url": "https://...",
      "description": "...",
      "timestamp": "2026-04-01T12:00:00"
    },
    "timestamp": "2026-04-01T12:00:00"
  }
}
```

### Configuration

```python
from version_manager import VersionManager
from datetime import timedelta

# Durée du cache
VersionManager.CACHE_DURATION = timedelta(hours=12)

# Dossier du cache
VersionManager.CACHE_DIR = "/custom/path"
```

## ⚠️ Exceptions et Erreurs

### Erreurs Gérées

- `requests.exceptions.Timeout` - Timeout GitHub
- `requests.exceptions.RequestException` - Erreurs réseau
- `ValueError` - Version invalide
- `OSError` - Erreurs fichier/disque

### Logging

Tous les erreurs sont loggées via `logging`:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
# Les logs s'afficheront
```

## 🎯 Exemples Complets

### Exemple 1: Vérification Simple

```python
from version_manager import get_github_checker

checker = get_github_checker()
info = checker.check_for_updates()

if info and info["update_available"]:
    print(f"Update to {info['latest']}")
```

### Exemple 2: Avec Mise à Jour

```python
from update_manager import get_update_manager

um = get_update_manager()

def handle(info):
    if info and info["update_available"]:
        if um.show_update_prompt(info):
            um.perform_update(info["url"])

um.check_async(handle)
```

### Exemple 3: Comparaison

```python
from version_manager import VersionInfo, get_version_manager

vm = get_version_manager()
current = vm.get_current_version()

if VersionInfo("1.0.0") > current:
    print("Upgrade available")
```

---

**Version**: 1.0
**Status**: Complete ✅

