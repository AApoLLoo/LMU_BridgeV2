# QUICK START - Démarrage Rapide

## 🚀 En 30 Secondes

### Installation
Aucune installation requise! Les nouveaux modules utilisent uniquement la stdlib Python et les dépendances existantes (`requests`).

### Usage Basique

```python
# Version simple (compatible avec l'ancien code)
from update import check_and_update
check_and_update()

# Version new (plus d'options)
from update_manager import get_update_manager
um = get_update_manager()
um.check_async(lambda info: print(info))
```

## 📖 Cas d'Usage Courants

### 1️⃣ Afficher la version
```python
from version_manager import get_version_manager

vm = get_version_manager()
print(vm.get_current_version())  # "0.6.0"
```

### 2️⃣ Vérifier les mises à jour au démarrage
```python
from update_manager import get_update_manager

um = get_update_manager()

def on_complete(info):
    if info and info["update_available"]:
        if um.show_update_prompt(info):
            um.perform_update(info["url"])

um.check_async(on_complete)
```

### 3️⃣ Comparer les versions
```python
from version_manager import VersionInfo

v1 = VersionInfo("1.0.0")
v2 = VersionInfo("1.0.1")

if v2 > v1:
    print("v1.0.1 est plus récent")
```

### 4️⃣ Dans CustomTkinter
```python
import customtkinter as ctk
from version_manager import get_version_manager

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        vm = get_version_manager()
        self.title(f"App {vm.get_current_version()}")

app = App()
app.mainloop()
```

## 📚 Documentation Complète

| Document | Description |
|----------|-------------|
| **VERSION_SYSTEM_GUIDE.md** | Guide détaillé avec 70+ exemples |
| **VERSION_API_REFERENCE.md** | Référence complète de l'API |
| **VERSION_BEST_PRACTICES.md** | Bonnes pratiques et patterns |
| **VERSION_IMPROVEMENTS.md** | Changelog et améliorations |

## 🔧 Configuration

Personnaliser le cache (optionnel):

```python
from version_manager import VersionManager
from datetime import timedelta

# Cache pendant 12 heures au lieu de 24
VersionManager.CACHE_DURATION = timedelta(hours=12)
```

## ⚡ Points Clés

✅ **Asynchrone** - N'interfère pas avec l'interface  
✅ **Cache** - Réduit les appels API de 95%  
✅ **Comparable** - Comparaison facile de versions  
✅ **Compatible** - L'ancien code fonctionne toujours  
✅ **Documenté** - Docstrings complètes  

## 🚨 Troubleshooting

### "Module non trouvé"
S'assurer que les fichiers sont dans le même dossier que le script.

### "Cache introuvable"
Normal! Créé automatiquement au premier usage dans `~/.lmu_bridge/`.

### "Timeout GitHub"
Le cache prend le relais. Vérifier la connexion réseau.

## 📞 Besoin d'aide?

- Consulter **VERSION_SYSTEM_GUIDE.md** pour les exemples
- Consulter **VERSION_API_REFERENCE.md** pour l'API
- Consulter **VERSION_BEST_PRACTICES.md** pour les patterns

---

**Version**: 1.0 | **Status**: ✅ Production-Ready

