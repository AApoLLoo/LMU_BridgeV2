import requests
import json
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
BASE_URL = "http://localhost:6397"  # Essayez 6397 si 5397 ne marche pasREFRESH_RATE = 1.0  # Rafraîchissement toutes les x secondes

# Liste des endpoints GET à surveiller
ENDPOINTS = [
    "/rest/watch/sessionInfo",  # Info Session (Circuit, Temps)
    "/rest/sessions/weather",  # Météo
    "/rest/strategy/usage",  # Conso Essence
    "/rest/strategy/pitstop-estimate",  # Est. Pitstop
    "/rest/watch/standings",  # Classement (Gros morceau)
    "/rest/garage/tireinfo",  # Info Pneus
    "/rest/race/car",  # Info Ma Voiture
]


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def fetch_data(endpoint):
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, timeout=0.5)  # Timeout court pour ne pas bloquer
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None


def compact_print(data, indent=2):
    """Affiche les données intelligemment (coupe les listes trop longues)"""
    if isinstance(data, list):
        print(f"{' ' * indent}[Liste de {len(data)} éléments]")
        # On affiche seulement les 3 premiers pour ne pas inonder la console
        for i, item in enumerate(data[:3]):
            print(f"{' ' * (indent + 2)}Item {i + 1}: {str(item)[:100]}...")  # Coupe les lignes trop longues
        if len(data) > 3:
            print(f"{' ' * (indent + 2)}... ({len(data) - 3} autres éléments masqués)")
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{' ' * indent}{key}:")
                compact_print(value, indent + 4)  # Récursion
            else:
                print(f"{' ' * indent}{key}: {value}")
    else:
        print(f"{' ' * indent}{data}")


def main():
    print("Démarrage du moniteur... (Ctrl+C pour arrêter)")
    time.sleep(1)

    while True:
        try:
            # On stocke tout avant d'afficher pour éviter le scintillement pendant le chargement
            results = {}
            for ep in ENDPOINTS:
                results[ep] = fetch_data(ep)

            # Rendu Graphique
            clear_screen()
            print(f"=== LMU LIVE MONITOR === {datetime.now().strftime('%H:%M:%S')}")
            print(f"Connecté à : {BASE_URL}")
            print("=" * 50)

            for endpoint, data in results.items():
                print(f"\n📂 ENDPOINT : {endpoint}")
                print("-" * 30)

                if data is None:
                    print("   ❌ Pas de données (Jeu fermé ou endpoint vide)")
                else:
                    compact_print(data)

            print("\n" + "=" * 50)
            print("Ctrl+C pour quitter")

            time.sleep(REFRESH_RATE)

        except KeyboardInterrupt:
            print("\nArrêt du script.")
            break
        except Exception as e:
            print(f"Erreur globale : {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()