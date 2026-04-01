# Guide d'Utilisation - LMU Bridge UI Amélioré v0.6.0

## 🎯 Qu'est-ce qui a changé ?

L'interface utilisateur du LMU Bridge a été entièrement redesignée avec un focus sur :
- ✨ **Design moderne** avec palette de couleurs enrichie
- 🎨 **Meilleure organisation** avec sections clairement séparées
- 🚀 **Interactions plus claires** avec emojis et feedback visuel
- 📱 **Interface scrollable** pour plus de contenu sans limitation de taille

## 🚀 Comment Démarrer

### Installation des dépendances
```bash
pip install customtkinter requests
```

### Lancement de l'application
```bash
python bridge.py
```

L'interface s'ouvrira avec la nouvelle présentation design.

## 📋 Sections de l'Interface

### 1️⃣ En-tête (Header)
- Logo "⚡ FBT RACING" en gros
- Sous-titre "Secure Telemetry Bridge"
- Barre accent colorée au-dessus (gradient bar)

### 2️⃣ Section Identifiants (📋)
Saisissez vos infos de connexion :
- **ID LineUp** : Nom unique de votre équipe
- **Pseudo** : Votre nom d'utilisateur
- **Mot de passe** : Votre mot de passe (masqué avec *)

### 3️⃣ Section Options (⚙️)
Configurez l'application :
- **🔐 Sauvegarder mot de passe** : Mémorise vos identifiants
- **📊 Enregistrer pour analyse** : Active l'enregistrement des données
- **🔧 Mode debug** : Affiche des logs détaillés pour diagnostic

### 4️⃣ Statut Connexion (📡)
Indicateurs de connexion :
- **JEU** : État de la connexion avec le jeu RF2
  - 🟡 EN ATTENTE : Jeu non encore détecté
  - 🟢 CONNECTÉ : Jeu trouvé
  - 🔴 OFFLINE : Déconnecté
  
- **VPS** : État du serveur cloud
  - 🟢 CONNECTÉ : Serveur accessible
  - 🟡 CONNEXION... : En cours de connexion
  - 🔴 OFFLINE : Serveur inaccessible

### 5️⃣ Boutons d'Action
- **🚀 CONNEXION & START** : Lance le bridge (avant connexion)
- **⛔ DÉCONNEXION** : Arrête le bridge (pendant connexion)

### 6️⃣ Journal d'Activité (📝)
Affiche les événements en temps réel :
- Horodatage de chaque message [HH:MM:SS]
- Utilisation d'emojis pour les types :
  - 🔐 Authentification
  - ✅ Succès
  - ❌ Erreur
  - 🎮 Jeu
  - 🏁 Session
  - 📊 Données
  - ⚠️ Avertissement

**Bouton 🗑 Effacer** : Nettoie le journal

## 🎨 Palette de Couleurs

### Meanings des Couleurs
```
🟣 Indigo (#6366F1)      = Actions principales, accent
🟢 Vert (#10B981)        = Succès, connecté
🔴 Rouge (#EF4444)       = Erreur, danger
🟠 Ambre (#F59E0B)       = Avertissement, info
🟪 Violet (#A855F7)      = Debug, informations techniques
⚫ Gris (#64748B)         = Texte secondaire, inactif
```

## 💡 Workflow Typique

1. **Remplir les Identifiants**
   ```
   ID LineUp: MyTeam
   Pseudo: JohnDoe
   Mot de passe: ••••••••
   ```

2. **Configurer les Options**
   ```
   ☑ Sauvegarder mot de passe
   ☑ Enregistrer pour analyse
   ☐ Mode debug
   ```

3. **Cliquer "🚀 CONNEXION & START"**
   - Le statut change à "CONNEXION..."
   - Attendre que "VPS: CONNECTÉ" s'affiche
   - Le jeu doit aussi se connecter (JEU: CONNECTÉ)

4. **Lancer le jeu RF2**
   - Démarrer RFactor2
   - Joindre une session
   - Le bridge detectera votre présence

5. **Monitorer via les logs**
   ```
   [09:45:23] 🔐 Authentification...
   [09:45:24] ✅ IDENTIFICATION OK
   [09:45:25] 🎮 Jeu connecté !
   [09:45:26] 🏁 Session : RACE
   [09:45:27] 📊 En attente (PIT / SPECTATE)
   ```

6. **Cliquer "⛔ DÉCONNEXION" pour arrêter**

## ⚙️ Modes Spéciaux

### Mode Debug
Activez la case "🔧 Mode debug" pour :
- Voir tous les payloads envoyés
- Diagnostiquer les problèmes de connexion
- Affichage toutes les 3 secondes (pour ne pas spammer)

### Enregistrement d'Analyse
Activez "📊 Enregistrer pour analyse" pour :
- Enregistrer les tours en détail
- Sauvegarder la telémétrie complète
- Permettre l'analyse ultérieure des données

## 🐛 Résolution des Problèmes

### "JEU: EN ATTENTE" (pas de changement)
→ Vérifiez que RFactor2 est lancé et que le plugin LMU est activé

### "VPS: OFFLINE"
→ Vérifiez votre connexion internet
→ Vérifiez que vos identifiants sont corrects
→ Consultez les logs pour le message d'erreur exact

### Les logs ne s'affichent pas
→ Cliquez le bouton "🗑 Effacer" pour réinitialiser
→ Attendez le prochain événement

## 📊 Indicateurs Visuels

Les points colorés (●) devant chaque statut changent de couleur :
- **Gris foncé** = Inactif/Non connecté
- **Orange** = En cours de traitement
- **Vert** = Connecté et fonctionnel
- **Rouge** = Erreur

## 🔧 Configuration Avancée

Les configurations sont sauvegardées dans `config.json` :
```json
{
  "lineup_id": "MyTeam",
  "pseudo": "JohnDoe",
  "password": "••••••••" (si "Sauvegarder" est coché)
}
```

## 📱 Responsive Design

L'interface se redimensionne correctement à 550x1000px. 
Pour des écrans plus petits, utilisez la molette de souris pour scroller.

## ❓ FAQ

**Q: Où sont stockées mes données ?**
A: Localement dans `config.json` à côté de bridge.py

**Q: Mon mot de passe est-il sécurisé ?**
A: Il est stocké en clair localement. Ne le sauvegardez que si votre PC est sécurisé.

**Q: Puis-je utiliser plusieurs instances ?**
A: Non recommandé. Une seule instance à la fois.

**Q: Les logs s'effacent automatiquement ?**
A: Oui, à chaque déconnexion/reconnexion.

---

**Version**: 0.6.0
**Design**: Modern Dark Theme
**Status**: Production Ready ✅
**Last Updated**: 2026-04-01

