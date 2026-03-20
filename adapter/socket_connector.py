import socketio
import requests
import time


class SocketConnector:
    def __init__(self, server_url, port=5000, username=None, password=None, log_callback=None):
        # Construction de l'URL
        if server_url.startswith("http"):
            self.base_url = f"{server_url}:{port}" if port else server_url
        else:
            self.base_url = f"http://{server_url}:{port}"

        self.sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=1)
        self.is_connected = False
        self.token = None

        # Identifiants de l'utilisateur du Bridge
        self.username = username
        self.password = password
        self._log = log_callback if log_callback else print

        @self.sio.event
        def connect():
            self._log("✅ SocketIO: Connecté au VPS (Authentifié) !")
            self.is_connected = True

        @self.sio.event
        def connect_error(data):
            self._log(f"❌ Erreur connexion Socket: {data}")

        @self.sio.event
        def disconnect():
            self._log("❌ SocketIO: Déconnecté du VPS")
            self.is_connected = False

        @self.sio.event
        def access_denied(msg):
            self._log(f"⛔ ACCÈS REFUSÉ: {msg}")
            self._log("👉 Rejoignez l'équipe sur le site Web !")

        @self.sio.event
        def error(msg):
            self._log(f"⚠️ Erreur Serveur VPS: {msg}")

    def login(self):
        """Authentifie le bridge auprès de l'API pour récupérer un Token JWT"""
        if not self.username or not self.password:
            self._log("⚠️ Pas d'identifiants (username/password). Le Bridge risque d'être rejeté.")
            return False

        try:
            self._log(f"🔐 Authentification pour '{self.username}'...")
            response = requests.post(f"{self.base_url}/api/auth/login", json={
                "username": self.username,
                "password": self.password
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self._log("🔓 Authentification réussie ! Token récupéré.")
                return True
            else:
                self._log(f"❌ Échec Authentification: {response.text}")
                return False
        except Exception as e:
            self._log(f"❌ Erreur réseau lors du login: {e}")
            return False

    def connect(self):
        if self.sio.connected:
            return

        # 1. On tente de se loguer si on n'a pas de token
        if not self.token:
            if not self.login():
                self._log("⚠️ Connexion sans token (risque de rejet pour la télémétrie)")

        # 2. Connexion Socket avec le Token en Auth
        try:
            auth_payload = {'token': self.token} if self.token else {}

            self._log(f"🔌 Connexion Socket vers {self.base_url}...")
            self.sio.connect(
                self.base_url,
                auth=auth_payload,
                wait_timeout=10
            )
        except Exception as e:
            self._log(f"⚠️ Erreur de connexion Socket: {e}")

    def send_data(self, data):
        # Connexion auto si besoin
        if not self.sio.connected:
            self.connect()
            if not self.sio.connected: return

        try:
            self.sio.emit('telemetry_data', data)
        except Exception as e:
            self._log(f"Erreur d'envoi: {e}")

    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()
