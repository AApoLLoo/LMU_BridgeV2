# LMU Bridge - UI Design Details

## 📐 Layout Structure

```
┌─────────────────────────────────────────┐
│  ═══════════════════════════════════════ │ ← Gradient Bar (Accent Color)
│           ⚡ FBT RACING                 │
│     Secure Telemetry Bridge             │
├─────────────────────────────────────────┤
│  📋 IDENTIFIANTS                        │
│  ┌─────────────────────────────────────┐│
│  │ ID LineUp (Nom Team)              ││
│  ├─────────────────────────────────────┤│
│  │ Votre Pseudo (Compte)             ││
│  ├─────────────────────────────────────┤│
│  │ Mot de passe Compte   [masked]    ││
│  └─────────────────────────────────────┘│
│                                         │
│  ⚙️ OPTIONS                             │
│  ┌─────────────────────────────────────┐│
│  │ ☐ 🔐 Sauvegarder mot de passe     ││
│  │ ☐ 📊 Enregistrer pour analyse     ││
│  │ ☐ 🔧 Mode debug (logs détaillés)  ││
│  └─────────────────────────────────────┘│
│                                         │
│  📡 STATUT CONNEXION                    │
│  ┌─────────────────────────────────────┐│
│  │ ● JEU: EN ATTENTE                  ││
│  ├─────────────────────────────────────┤│
│  │ ● VPS: OFFLINE                     ││
│  └─────────────────────────────────────┘│
│                                         │
│  ┌─────────────────────────────────────┐│
│  │ 🚀 CONNEXION & START                ││
│  └─────────────────────────────────────┘│
│                                         │
│  📝 JOURNAL D'ACTIVITÉ           🗑     │
│  ┌─────────────────────────────────────┐│
│  │ [09:45:23] 🔐 Authentification...  ││
│  │ [09:45:24] ✅ IDENTIFICATION OK   ││
│  │ [09:45:25] 🎮 Jeu connecté !      ││
│  │ [09:45:26] 🏁 Session : RACE      ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

## 🎨 Color Usage Map

### Header Section
- **Gradient Bar**: Accent (#6366F1)
- **Title**: Accent Light (#818CF8)
- **Subtitle**: Text Subdim (#475569)

### Input Fields
- **Background**: Card (#1A2336)
- **Border**: Border (#334155)
- **Text**: Text (#F8FAFC)
- **Placeholder**: Text Dim (#64748B)

### Buttons
- **Start Button**:
  - Background: Accent (#6366F1)
  - Hover: Accent Hover (#4F46E5)
  - Text: Text (#F8FAFC)

- **Stop Button**:
  - Background: Danger (#EF4444)
  - Hover: Danger Hover (#DC2626)
  - Text: Text (#F8FAFC)

- **Clear Button**:
  - Background: Card (#1A2336)
  - Hover: Danger (#EF4444)
  - Text: Text Dim (#64748B)

### Status Indicators
- **Inactive**: Text Dim (#64748B)
- **Warning**: Warning (#F59E0B)
- **Success**: Success (#10B981)
- **Error**: Danger (#EF4444)
- **Connected**: Accent (#6366F1)

### Log Area
- **Background**: #0F1419 (Nearly black)
- **Text**: #4ADE80 (Terminal green)
- **Font**: Consolas monospace
- **Border**: Border (#334155)

## 📏 Spacing & Sizing

| Element | Size | Padding |
|---------|------|---------|
| Window | 550x1000px | - |
| Header Title | 38px bold | 20px vertical |
| Section Headers | 12px bold | 15px all |
| Input Fields | 45px height | 20px horizontal |
| Card Radius | 12px | - |
| Button Height | 55px | 20px horizontal |
| Logs Height | 150px | 20px horizontal |
| Status Row Height | 50px | 15px padding |

## 🎯 Interaction States

### Button States
- **Normal**: Color displayed
- **Hover**: Lighter/darker shade with cursor change
- **Disabled**: Dimmed with no cursor change
- **Active/Pressed**: Slightly darker with slight inset

### Field States
- **Focus**: Border color enhanced
- **Disabled**: Greyed out, no cursor
- **Valid**: Normal appearance
- **Error**: Could highlight with warning color (future)

### Status Dot States
- ● **Blinking/Pulsing** (animated - future enhancement)
- Colors match connection state
- Larger size (16px) for visibility

## 💡 Design Principles Used

1. **Visual Hierarchy**: Clear section headers with emojis
2. **Color Psychology**: Green for success, red for errors, amber for warnings
3. **Consistency**: Repeated patterns and spacing
4. **Accessibility**: Large text, clear contrasts
5. **Professional Look**: Modern dark theme with quality typography
6. **User Feedback**: Status indicators, button states, log output

## 🔮 Animation Possibilities

- Gradient bar subtle animation on connection
- Status dot pulsing during connecting
- Button scale effect on hover
- Log entries fade-in animation
- Smooth transitions between states

---
**Design Version**: 0.6.0
**Last Updated**: 2026-04-01

