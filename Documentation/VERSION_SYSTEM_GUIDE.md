# Guide du Système de Versioning Amélioré

## 📋 Vue d'ensemble

Le système de versioning a été complètement refondu pour être **plus fluide, intuitif et maintenable**. Il est maintenant composé de trois modules:

- **`version_manager.py`** - Gestion centralisée des versions
- **`update_manager.py`** - Gestion des mises à jour  
- **`update.py`** - Couche de compatibilité (legacy)

## 🚀 Caractéristiques principales

### ✅ Améliorations

1. **Meilleure séparation des responsabilités**
   - Versioning distinct des mises à jour
   - Code modulaire et réutilisable

2. **Cache intelligent**
   - Les requêtes GitHub sont mises en cache pendant 24h
   - Réduit les appels API inutiles
   - Stockage dans `~/.lmu_bridge/version_cache.json`

3. **Comparaison de versions sophistiquée**
   - Support complet des versions SemVer (1.2.3)
   - Opérateurs de comparaison: `<`, `<=`, `==`, `!=`, `>`, `>=`
   - Gestion des versions prérelease

4. **Interface uniforme**
   - API simple et intuitive
   - Fonctions helper pour les cas d'usage courants
   - Gestion d'erreurs cohérente

5. **Opérations asynchrones**
   - Les vérifications de mise à jour ne bloquent pas l'interface
   - Callbacks pour la gestion des résultats

## 📚 Usage

### Version Manager (Gestion des versions)

```python
from version_manager import get_version_manager, VersionInfo

# Récupérer le gestionnaire
vm = get_version_manager()

# Obtenir la version courante
current = vm.get_current_version()
print(f"Version actuelle: {current}")  # "0.6.0"

# Comparer les versions
v1 = VersionInfo("1.0.0")
v2 = VersionInfo("1.0.1")

if v2 > v1:
    print("v1.0.1 est plus récent que v1.0.0")

# Comparaison avec tuples
if v1.tuple < v2.tuple:
    print("Comparaison par tuple fonctionne aussi")

# Informations de version
print(vm.format_version_info())  # "LMU_Bridge 0.6.0"
print(vm.get_python_version())  # "3.11.5"
```

### GitHub Release Checker (Vérification des releases)

```python
from version_manager import get_github_checker

# Récupérer le vérificateur
checker = get_github_checker("AApoLLoo/LMU_BridgeV2")

# Vérifier les mises à jour
update_info = checker.check_for_updates()

if update_info:
    if update_info["update_available"]:
        print(f"Mise à jour disponible: {update_info['latest']}")
        print(f"URL: {update_info['url']}")
        print(f"Description: {update_info['description']}")
```

### Update Manager (Gestion des mises à jour)

```python
from update_manager import get_update_manager

# Récupérer le gestionnaire
um = get_update_manager("AApoLLoo/LMU_BridgeV2")

# Vérifier asynchronement
def on_check_complete(update_info):
    if update_info and update_info.get("update_available"):
        if um.show_update_prompt(update_info):
            um.perform_update(update_info["url"])

um.check_async(on_check_complete)
```

### Compatibilité Legacy (update.py)

```python
from update import check_and_update, get_latest_release_info

# Utiliser l'API classique
check_and_update()

# Ou manuellement
version, url = get_latest_release_info()
if version:
    print(f"Dernière version: {version}")
```

## 🏗️ Architecture

### Version Flow

```
version.py (définition)
    ↓
VersionInfo (comparaison)
    ↓
VersionManager (gestion)
    ↓
GitHubReleaseChecker (détection)
    ↓
UpdateManager (mise à jour)
```

### Cache Flow

```
Requête API
    ↓
Cache valide? → OUI → Retourner du cache
    ↓ NON
Requêter GitHub
    ↓
Sauvegarder dans cache
    ↓
Retourner résultat
```

## ⚙️ Configuration

### Cache Duration

Par défaut, le cache expire après **24 heures**. Pour modifier:

```python
from version_manager import VersionManager
from datetime import timedelta

VersionManager.CACHE_DURATION = timedelta(hours=12)
```

### Repository

Pour utiliser un autre repository:

```python
from version_manager import get_github_checker

checker = get_github_checker("votre-user/votre-repo")
```

## 🐛 Logging

Les logs sont disponibles via le module `logging`:

```python
import logging

# Récupérer les logs
logger = logging.getLogger("version_manager")
logger.debug("Message de debug")

# Voir les logs du cache
logger.info("Cache utilisé")
```

## 📝 Migration depuis l'ancien système

### Avant
```python
from update import check_and_update
from version import __version__

check_and_update()
print(f"Version: {__version__}")
```

### Après
```python
from update import check_and_update
from version_manager import get_version_manager

check_and_update()  # Fonctionne toujours!
vm = get_version_manager()
print(f"Version: {vm.get_current_version()}")
```

## 🔧 Exemples avancés

### Vérifier et afficher les détails

```python
from version_manager import get_github_checker

checker = get_github_checker()
release = checker.get_latest_release()

if release:
    print(f"✓ Version: {release['version']}")
    print(f"✓ Description: {release['description'][:100]}...")
    print(f"✓ URL: {release['url']}")
```

### Forcer une nouvelle vérification (ignorer cache)

```python
from version_manager import get_github_checker

checker = get_github_checker()
release = checker.get_latest_release(use_cache=False)
```

### Comparer les versions

```python
from version_manager import VersionInfo, get_version_manager

vm = get_version_manager()
current = vm.get_current_version()

comparison = vm.compare_versions("1.0.0", "1.0.1")
# -1 si 1.0.0 < 1.0.1
#  0 si égal
#  1 si 1.0.0 > 1.0.1
```

## ✨ Avantages du nouveau système

| Aspect | Avant | Après |
|--------|-------|-------|
| **Modularité** | Mélangé | Séparé |
| **Cache** | Aucun | 24h par défaut |
| **Comparaison** | Simple | Complète (SemVer) |
| **Async** | Non | Oui |
| **Logging** | Basique | Détaillé |
| **Tests** | Difficile | Facile |
| **Maintenabilité** | Faible | Haute |

## 🚨 Dépannage

### "Impossible de charger le module 'version'"

Assurez-vous que `version.py` existe avec une variable `__version__`.

### "Timeout lors de la connexion à GitHub"

GitHub est peut-être indisponible ou votre connexion est lente. Le système essaiera utiliser le cache.

### Cache pas mis à jour

Le cache expire après 24h. Pour forcer une actualisation:

```python
checker.get_latest_release(use_cache=False)
```

## 📞 Support

Pour plus d'informations ou pour signaler un bug, veuillez consulter le README principal.

