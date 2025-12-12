import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import threading
import time
import sys
import os
import logging
import requests
from update import check_and_update
from version import __version__

# --- FIX IMPORT ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- IMPORT DES CONNECTEURS ---
try:
    from adapter.rf2_connector import RF2Info
    from adapter.restapi_connector import RestAPIInfo
    from adapter.rf2_data import (
        TelemetryData, ScoringData, RulesData, ExtendedData,
        PitInfoData, WeatherData, PitStrategyData, Vehicle
    )
    from adapter.socket_connector import SocketConnector
except ImportError as e:
    print(f"Erreur d'import critique : {e}")
    sys.exit(1)

COLORS = {
    "bg": "#0f172a", "panel": "#1e293b", "input": "#334155",
    "text": "#f8fafc", "accent": "#6366f1", "success": "#10b981",
    "danger": "#ef4444", "warning": "#eab308", "debug": "#a855f7"
}

# --- CONFIGURATION VPS ---
VPS_URL = "https://api.racetelemetrybyfbt.com"


def normalize_id(name):
    import re
    safe = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()
    return safe


class MockParentAPI:
    def __init__(self):
        self.identifier = "LMU"
        self.isActive = True


# --- CALCULATEUR DE CONSOMMATION ---
class ConsumptionTracker:
    def __init__(self, log_func):
        self.log = log_func
        self.reset()

    def reset(self):
        self.last_lap = -1
        self.fuel_start = -1.0
        self.ve_start = -1.0
        self.fuel_last = 0.0
        self.fuel_avg = 0.0
        self.fuel_samples = 0
        self.ve_last = 0.0
        self.ve_avg = 0.0
        self.ve_samples = 0

    def update(self, current_lap, current_fuel, current_ve, in_pits):
        if self.last_lap == -1 or current_lap < self.last_lap:
            self.last_lap = current_lap
            self.fuel_start = current_fuel
            self.ve_start = current_ve
            if current_lap < self.last_lap and self.last_lap != -1:
                self.log("🔄 Session redémarrée : Reset conso")
            return

        if current_lap > self.last_lap:
            fuel_delta = self.fuel_start - current_fuel
            ve_delta = self.ve_start - current_ve

            if not in_pits and fuel_delta > 0.01:
                self.fuel_last = fuel_delta
                self.fuel_samples += 1
                self.fuel_avg = self.fuel_avg + (fuel_delta - self.fuel_avg) / self.fuel_samples
                self.log(f"🏁 Tour {self.last_lap} terminé. Conso: {fuel_delta:.2f}L")

                if ve_delta > 0.01:
                    self.ve_last = ve_delta
                    self.ve_samples += 1
                    self.ve_avg = self.ve_avg + (ve_delta - self.ve_avg) / self.ve_samples

            elif in_pits:
                self.log(f"🛑 Tour {self.last_lap} ignoré (Stands)")

            self.last_lap = current_lap
            self.fuel_start = current_fuel
            self.ve_start = current_ve

    def get_stats(self):
        return {
            "lastLapFuelConsumption": round(self.fuel_last, 2),
            "averageConsumptionFuel": round(self.fuel_avg, 2),
            "lastLapVEConsumption": round(self.ve_last, 2),
            "averageConsumptionVE": round(self.ve_avg, 2)
        }


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            try:
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, "• " + msg + '\n')
                self.text_widget.see(tk.END)
                self.text_widget.config(state=tk.DISABLED)
            except:
                pass

        self.text_widget.after(0, append)


class TelemetryRecorder:
    def __init__(self, api_url, team_id):
        self.api_url = api_url
        self.team_id = team_id
        self.buffer = []
        self.current_lap = -1
        self.driver_name = "Unknown"
        self.track_name = "Unknown"
        self.last_dist = -1

    def update(self, lap_number, vehicle_idx, telemetry, vehicle, scoring):
        if self.current_lap != -1 and lap_number > self.current_lap:
            last_lap_time = 0
            if hasattr(scoring, 'get_vehicle_scoring'):
                v_data = scoring.get_vehicle_scoring(vehicle_idx)
                last_lap_time = v_data.get('last_lap', 0)

            self.flush_lap(self.current_lap, last_lap_time)
            self.buffer = []
            self.last_dist = -1

        self.current_lap = lap_number
        dist = 0
        if hasattr(telemetry, 'lap_distance'):
            dist = telemetry.lap_distance(vehicle_idx)
        if (dist == 0 or dist is None) and hasattr(scoring, 'get_vehicle_scoring'):
            v_data = scoring.get_vehicle_scoring(vehicle_idx)
            dist = v_data.get('lap_dist', 0)

        if vehicle.speed(vehicle_idx) > 1:
            if self.last_dist == -1 or abs(dist - self.last_dist) > 2.0:
                self.buffer.append({
                    "d": round(dist, 1),
                    "s": round(vehicle.speed(vehicle_idx), 1),
                    "t": round(telemetry.input_throttle(vehicle_idx) * 100, 0),
                    "b": round(telemetry.input_brake(vehicle_idx) * 100, 0),
                    "g": telemetry.gear(vehicle_idx),
                    "w": round(telemetry.input_steering(vehicle_idx), 2),
                    "f": round(telemetry.fuel_level(vehicle_idx), 2),
                    "r": round(telemetry.rpm(vehicle_idx), 0),
                    "ve": round(telemetry.virtual_energy(vehicle_idx), 1),
                    "tw": round(telemetry.tire_wear(vehicle_idx)[0], 1)
                })
                self.last_dist = dist

    def flush_lap(self, lap_num, lap_time):
        if not self.buffer or len(self.buffer) < 50: return
        payload = {
            "sessionId": self.team_id,
            "lapNumber": lap_num,
            "driver": self.driver_name,
            "lapTime": lap_time,
            "samples": self.buffer
        }

        def send():
            try:
                requests.post(f"{self.api_url}/api/telemetry/lap", json=payload,
                              headers={"Content-Type": "application/json"}, timeout=5)
                print(f"💾 Télémétrie Tour {lap_num} sauvegardée")
            except Exception as e:
                print(f"⚠️ Erreur upload télémétrie: {e}")

        threading.Thread(target=send, daemon=True).start()


class BridgeLogic:
    def __init__(self, log_callback, status_callback):
        self.log = log_callback
        self.set_status = status_callback
        self.running = False
        self.debug_mode = False
        self.connector = None
        self.rf2_info = None
        self.rest_info = None
        self.thread = None
        self.line_up_name = ""
        self.team_id = ""
        self.driver_pseudo = ""
        self.tracker = ConsumptionTracker(self.log)
        self.session_id = 0
        self.recorder = None
        self.analysis_enabled = False

    def set_debug(self, enabled):
        self.debug_mode = enabled
        self.log(f"🔧 Mode Debug {'ACTIVÉ' if enabled else 'DÉSACTIVÉ'}")

    def connect_vps(self):
        if self.connector and self.connector.is_connected: return True
        try:
            self.connector = SocketConnector(VPS_URL, port=None)
            self.connector.connect()
            return True
        except Exception as e:
            self.log(f"❌ Erreur Connexion VPS: {e}")
            return False

    def start_loop(self, line_up_name, driver_pseudo, analysis_enabled):
        self.session_id += 1
        current_session_id = self.session_id
        self.line_up_name = line_up_name
        self.team_id = normalize_id(line_up_name)
        self.driver_pseudo = driver_pseudo
        self.analysis_enabled = analysis_enabled
        self.running = True
        self.tracker.reset()

        if self.analysis_enabled:
            self.log("📊 Enregistrement Analyse : ACTIVÉ")
        else:
            self.log("🚫 Enregistrement Analyse : DÉSACTIVÉ")

        if not self.connector: self.connect_vps()
        if self.connector and self.connector.is_connected:
            self.log(f"💾 Connexion pour '{self.team_id}'...")
            self.connector.join_lineup(self.team_id, self.driver_pseudo)
        self.thread = threading.Thread(target=self._run, args=(current_session_id,), daemon=True)
        self.thread.start()

    def stop(self):
        self.log("🛑 Demande d'arrêt...")
        self.running = False
        self.session_id += 1
        try:
            if self.rf2_info: self.rf2_info.stop()
        except:
            pass
        try:
            if self.rest_info: self.rest_info.stop()
        except:
            pass
        try:
            if self.connector: self.connector.disconnect()
        except:
            pass
        self.rf2_info = None
        self.rest_info = None
        self.thread = None
        self.set_status("STOPPED", COLORS["danger"])
        self.log("⏹️ Bridge arrêté.")

    def _run(self, my_session_id):
        self.log(f"🚀 Démarrage session #{my_session_id} pour '{self.line_up_name}'")
        self.set_status("WAITING GAME...", COLORS["warning"])

        pit_strategy = PitStrategyData(port=6397)
        mock_parent = MockParentAPI()
        self.rest_info = RestAPIInfo(mock_parent)
        self.rest_info.setConnection({
            "url_host": "localhost", "url_port_lmu": 6397, "connection_timeout": 1.0,
            "connection_retry": 3, "connection_retry_delay": 2, "restapi_update_interval": 50,
            "enable_restapi_access": True, "enable_weather_info": True, "enable_session_info": True,
            "enable_garage_setup_info": True, "enable_vehicle_info": True, "enable_energy_remaining": True
        })

        telemetry = scoring = rules = extended = pit_info = weather = vehicle_helper = None
        last_game_check = 0
        last_update_time = 0
        UPDATE_RATE = 0.05
        last_session_type = -1
        current_history_id = f"{self.team_id}_WAITING"
        self.recorder = TelemetryRecorder(VPS_URL, current_history_id)

        # --- TRACKING : Stints & Pit Stops ---
        vehicle_trackers = {}

        while self.running:
            if self.session_id != my_session_id: break
            current_time = time.time()

            if self.rf2_info is None:
                if not self.running: break
                if current_time - last_game_check > 5.0:
                    try:
                        self.rf2_info = RF2Info()
                        self.rf2_info.start()
                        self.rest_info.start()
                        self.log("🎮 Jeu détecté ! Connexion établie.")
                        self.set_status("CONNECTED (GAME)", COLORS["success"])
                        telemetry = TelemetryData(self.rf2_info, self.rest_info)
                        scoring = ScoringData(self.rf2_info)
                        rules = RulesData(self.rf2_info)
                        extended = ExtendedData(self.rf2_info)
                        pit_info = PitInfoData(self.rf2_info)
                        weather = WeatherData(self.rf2_info)
                        vehicle_helper = Vehicle(self.rf2_info)
                        self.tracker.reset()
                        vehicle_trackers = {}
                    except Exception as e:
                        try:
                            if self.rf2_info: self.rf2_info.stop()
                        except:
                            pass
                        self.rf2_info = None
                    last_game_check = current_time
                time.sleep(0.1)
                continue

            try:
                if not self.running: break
                status = vehicle_helper.get_local_driver_status()

                # --- 1. DÉTECTION DU TYPE DE SESSION ---
                current_sess_name = "TEST"
                current_sess_type = 0

                if self.rf2_info and scoring:
                    try:
                        current_sess_type = scoring.session_type()
                        if 1 <= current_sess_type <= 4:
                            current_sess_name = "PRACTICE"
                        elif 5 <= current_sess_type <= 8:
                            current_sess_name = "QUALIFY"
                        elif current_sess_type == 9:
                            current_sess_name = "WARMUP"
                        elif current_sess_type >= 10:
                            current_sess_name = "RACE"

                        # Gestion changement de session
                        if current_sess_type != last_session_type:
                            current_history_id = f"{self.team_id}_{current_sess_name}_{int(time.time())}"
                            self.log(f"🔄 Nouvelle Séance : {current_sess_name} ({current_history_id})")
                            if self.recorder: self.recorder.team_id = current_history_id

                            vehicle_trackers = {}  # Reset stats

                            car_cat = "Unknown"
                            try:
                                veh_idx = status.get('vehicle_index', -1)
                                if veh_idx != -1:
                                    v_data = scoring.get_vehicle_scoring(veh_idx)
                                    car_cat = v_data.get('class', 'Unknown')
                            except:
                                pass

                            if self.connector:
                                self.connector.register_lineup(self.team_id, self.driver_pseudo, current_history_id,
                                                               current_sess_name, car_category=car_cat)

                                # --- GESTION ENREGISTREMENT ANALYSE ---
                                if self.analysis_enabled:
                                    try:
                                        track_name = scoring.track_name() if scoring else "Unknown Circuit"
                                        current_driver = status.get('driver_name', self.driver_pseudo)
                                        api_payload = {"sessionId": current_history_id, "driver": current_driver,
                                                       "circuit": track_name}
                                        requests.post(f"{VPS_URL}/api/sessions/start", json=api_payload, timeout=2)
                                        self.log(f"📁 Session d'analyse créée")
                                    except Exception as api_err:
                                        self.log(f"⚠️ Erreur création session Analyse: {api_err}")
                                # ---------------------------------------

                            last_session_type = current_sess_type
                    except Exception as e:
                        if self.debug_mode: self.log(f"Err session check: {e}")

                if self.rf2_info and scoring:
                    self.recorder.driver_name = status.get('driver_name', 'Unknown')
                    self.recorder.track_name = scoring.track_name() if scoring else "Unknown"

                if status['is_driving'] and (current_time - last_update_time > UPDATE_RATE):
                    idx = status['vehicle_index']
                    game_driver = status['driver_name']
                    curr_fuel = telemetry.fuel_level(idx)
                    curr_ve = telemetry.virtual_energy(idx)
                    curr_lap = telemetry.lap_number(idx)

                    # --- ENREGISTREMENT TÉLÉMÉTRIE (SI ACTIVÉ) ---
                    try:
                        if self.analysis_enabled:
                            self.recorder.update(curr_lap, idx, telemetry, vehicle_helper, scoring)
                    except:
                        pass
                    # ---------------------------------------------

                    # --- WEATHER ---
                    forecast_data = []
                    try:
                        if hasattr(weather, 'forecast'):
                            raw_forecast = weather.forecast()
                            key = 'race'
                            if current_sess_type < 5:
                                key = 'practice'
                            elif current_sess_type < 9:
                                key = 'qualify'

                            for node in raw_forecast.get(key, []):
                                forecast_data.append({
                                    "rain": float(node.get("rain_chance", 0.0)) / 100.0,
                                    "cloud": min(max(float(node.get("sky", 0)), 0) / 4.0, 1.0),
                                    "temp": float(node.get("temp", 0.0))
                                })
                    except:
                        pass

                    try:
                        scor_veh = scoring.get_vehicle_scoring(idx)
                        in_pits = (scor_veh.get('in_pits', 0) == 1)
                    except:
                        in_pits = False

                    self.tracker.update(curr_lap, curr_fuel, curr_ve, in_pits)
                    stats = self.tracker.get_stats()

                    # --- VEHICLE TRACKING ---
                    all_vehicles = []
                    try:
                        count = scoring.vehicle_count()
                        for i in range(count):
                            v = scoring.get_vehicle_scoring(i)

                            vid = v.get('id')
                            v_in_pits = (v.get('in_pits') == 1)
                            v_laps = v.get('laps', 0)
                            game_pit_count = v.get('pit_stops', 0)

                            if vid not in vehicle_trackers:
                                vehicle_trackers[vid] = {
                                    'last_pit_lap': v_laps if v_laps > 0 else 0,
                                    'was_in_pits': v_in_pits,
                                    'pit_count': game_pit_count
                                }

                            tracker = vehicle_trackers[vid]
                            if not tracker['was_in_pits'] and v_in_pits:
                                tracker['pit_count'] += 1
                            if tracker['was_in_pits'] and not v_in_pits:
                                tracker['last_pit_lap'] = v_laps

                            tracker['was_in_pits'] = v_in_pits
                            if game_pit_count > tracker['pit_count']:
                                tracker['pit_count'] = game_pit_count
                            if tracker['last_pit_lap'] > v_laps:
                                tracker['last_pit_lap'] = 0

                            v['stint_laps'] = max(0, v_laps - tracker['last_pit_lap'])
                            v['pit_stops'] = tracker['pit_count']

                            all_vehicles.append(v)
                    except:
                        pass

                    # Leader & Position
                    leader = next((v for v in all_vehicles if v['position'] == 1), None)
                    leader_laps = leader['laps'] if leader else 0

                    time_info = scoring.time_info()
                    time_info['session'] = current_sess_name

                    elapsed_time = time_info.get("current", 0)
                    leader_avg = 0
                    if leader_laps > 0 and elapsed_time > 0:
                        leader_avg = elapsed_time / leader_laps

                    # Calcul Position Joueur
                    my_position = scor_veh.get('position', 0)
                    my_class = scor_veh.get('class', '')
                    class_vehicles = [v for v in all_vehicles if v.get('class') == my_class]
                    class_vehicles.sort(key=lambda x: x.get('position', 999))
                    for i, v in enumerate(class_vehicles):
                        if v['id'] == scor_veh.get('id'):
                            my_position = i + 1
                            break
                    scor_veh['classPosition'] = my_position

                    payload = {
                        "teamId": self.team_id,
                        "driverName": game_driver,
                        "activeDriverId": self.driver_pseudo,
                        "lastLapFuelConsumption": stats["lastLapFuelConsumption"],
                        "averageConsumptionFuel": stats["averageConsumptionFuel"],
                        "lastLapVEConsumption": stats["lastLapVEConsumption"],
                        "averageConsumptionVE": stats["averageConsumptionVE"],
                        "sessionTimeRemainingSeconds": max(0, time_info.get("end", 0) - time_info.get("current", 0)),
                        "weatherForecast": forecast_data,
                        "telemetry": {
                            "gear": telemetry.gear(idx),
                            "rpm": telemetry.rpm(idx),
                            "speed": vehicle_helper.speed(idx),
                            "fuel": curr_fuel,
                            "fuelCapacity": telemetry.fuel_capacity(idx),
                            "inputs": {"thr": telemetry.input_throttle(idx), "brk": telemetry.input_brake(idx),
                                       "clt": telemetry.input_clutch(idx), "str": telemetry.input_steering(idx)},
                            "temps": {"oil": telemetry.temp_oil(idx), "water": telemetry.temp_water(idx)},
                            "tires": {"temp": telemetry.tire_temps(idx), "press": telemetry.tire_pressure(idx),
                                      "wear": telemetry.tire_wear(idx), "brake_wear": telemetry.brake_wear(idx),
                                      "type": telemetry.surface_type(idx),
                                      "brake_temp": telemetry.brake_temp(idx),
                                      "compounds": telemetry.tire_compound_name(idx)},
                            "electric": telemetry.electric_data(idx),
                            "virtual_energy": curr_ve,
                            "max_virtual_energy": 100.0,
                            "leaderLaps": leader_laps,
                            "leaderAvgLapTime": leader_avg,
                            "position": my_position,
                            "lastLap": telemetry.id(idx)
                        },
                        "scoring": {
                            "track": scoring.track_name(),
                            "time": time_info,
                            "flags": scoring.flag_state(),
                            "weather": scoring.weather_env(),
                            "vehicles": all_vehicles,
                            "vehicle_data": scor_veh
                        },
                        "rules": {
                            "sc": rules.sc_info(),
                            "yellow": rules.yellow_flag(),
                            "my_status": rules.participant_status(idx)
                        },
                        "pit": {
                            "menu": pit_info.menu_status(),
                            "strategy": pit_strategy.pit_estimate()
                        },
                        "weather_det": weather.info(),
                        "extended": {
                            "physics": extended.physics_options(),
                            "pit_limit": extended.pit_limit()
                        }
                    }

                    if self.running and self.session_id == my_session_id:
                        if self.connector: self.connector.send_data(payload)
                        last_update_time = current_time
                        self.set_status(f"LIVE ({game_driver}) P{my_position}", COLORS["accent"])

                elif not status['is_driving']:
                    self.set_status("IDLE (NOT DRIVING)", "#94a3b8")
                    time.sleep(0.5)

            except Exception as e:
                if self.running and self.session_id == my_session_id:
                    self.log(f"⚠️ Erreur boucle: {e}")
                    time.sleep(1.0)
                    try:
                        if self.rf2_info: self.rf2_info.stop()
                    except:
                        pass
                    self.rf2_info = None
                    self.set_status("RECONNECTING...", COLORS["warning"])
                else:
                    break
            time.sleep(0.01)


class BridgeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"LMU Telemetry Bridge (Python) - {__version__}")
        self.root.geometry("500x700")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))

        header_frame = tk.Frame(root, bg=COLORS["bg"])
        header_frame.pack(pady=20)
        tk.Label(header_frame, text="Property of FBT", font=("Segoe UI", 24, "bold italic"), bg=COLORS["bg"],
                 fg="white").pack()
        tk.Label(header_frame, text="CLOUD BRIDGE (PYTHON)", font=("Segoe UI", 10, "bold"), bg=COLORS["bg"],
                 fg=COLORS["accent"]).pack()

        form_frame = tk.Frame(root, bg=COLORS["panel"], padx=20, pady=20)
        form_frame.pack(padx=30, fill="x", pady=10)
        tk.Label(form_frame, text="NOM DE LA LINE UP (ID)", bg=COLORS["panel"], fg="#94a3b8",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.ent_lineup = tk.Entry(form_frame, bg=COLORS["input"], fg="white", font=("Segoe UI", 12), relief="flat",
                                   insertbackground="white")
        self.ent_lineup.pack(fill="x", pady=(5, 15), ipady=5)
        tk.Label(form_frame, text="VOTRE PSEUDO", bg=COLORS["panel"], fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(
            anchor="w")
        self.ent_pseudo = tk.Entry(form_frame, bg=COLORS["input"], fg="white", font=("Segoe UI", 12), relief="flat",
                                   insertbackground="white")
        self.ent_pseudo.pack(fill="x", pady=(5, 15), ipady=5)

        # --- OPTIONS (Checkboxes) ---
        options_frame = tk.Frame(form_frame, bg=COLORS["panel"])
        options_frame.pack(fill="x", pady=(0, 15))

        # Checkbox Analyse (Défaut: False)
        self.var_analysis = tk.BooleanVar(value=False)
        cb_analysis = tk.Checkbutton(options_frame, text="ENREGISTRER SESSION (ANALYSE)", variable=self.var_analysis,
                                     bg=COLORS["panel"], fg="white", selectcolor=COLORS["bg"],
                                     activebackground=COLORS["panel"], activeforeground="white",
                                     font=("Segoe UI", 9, "bold"))
        cb_analysis.pack(anchor="w")

        # Checkbox Debug (Défaut: False)
        self.var_debug = tk.BooleanVar(value=False)
        cb_debug = tk.Checkbutton(options_frame, text="MODE DEBUG (LOGS)", variable=self.var_debug,
                                  bg=COLORS["panel"], fg=COLORS["debug"], selectcolor=COLORS["bg"],
                                  activebackground=COLORS["panel"], activeforeground=COLORS["debug"],
                                  font=("Segoe UI", 8), command=self.toggle_debug)
        cb_debug.pack(anchor="w")
        # ----------------------------

        self.btn_start = tk.Button(form_frame, text="CONNEXION AU CLOUD", bg=COLORS["accent"], fg="white",
                                   font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", command=self.on_start)
        self.btn_start.pack(fill="x", ipady=8)
        self.btn_stop = tk.Button(form_frame, text="DÉCONNEXION", bg=COLORS["danger"], fg="white",
                                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", command=self.on_stop)
        self.lbl_status = tk.Label(root, text="READY", bg=COLORS["bg"], fg="#94a3b8", font=("Consolas", 10, "bold"))
        self.lbl_status.pack(pady=5)

        self.txt_log = scrolledtext.ScrolledText(root, bg="#020408", fg="#22c55e", font=("Consolas", 9), height=12,
                                                 relief="flat")
        self.txt_log.pack(fill="both", expand=True, padx=30, pady=(10, 30))
        self.txt_log.config(state=tk.DISABLED)
        handler = TextHandler(self.txt_log)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        self.logic = BridgeLogic(self.log, self.set_status)

    def toggle_debug(self):
        self.logic.set_debug(self.var_debug.get())

    def log(self, msg):
        self.root.after(0, lambda: self._log_safe(msg))

    def _log_safe(self, msg):
        try:
            self.txt_log.config(state=tk.NORMAL)
            if float(self.txt_log.index('end')) > 500: self.txt_log.delete('1.0', '100.0')
            self.txt_log.insert(tk.END, f"> {msg}\n")
            self.txt_log.see(tk.END)
            self.txt_log.config(state=tk.DISABLED)
        except:
            pass

    def set_status(self, text, color):
        self.root.after(0, lambda: self.lbl_status.config(text=text, fg=color))

    def on_start(self):
        l, p = self.ent_lineup.get().strip(), self.ent_pseudo.get().strip()
        ana = self.var_analysis.get()
        if not l or not p: return messagebox.showwarning("Info", "Remplissez les champs.")
        self.btn_start.config(state=tk.DISABLED, text="CONNEXION...")
        threading.Thread(target=self._check_and_start, args=(l, p, ana)).start()

    def _check_and_start(self, l, p, ana):
        if self.logic.connect_vps():
            self.log(f"☁️ Connecté au VPS !")
            self._activate_ui(True)
            self.logic.start_loop(l, p, ana)
        else:
            self.log("❌ Échec connexion VPS.")
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL, text="CONNEXION AU CLOUD"))

    def _activate_ui(self, active):
        if active:
            self.ent_lineup.config(state=tk.DISABLED);
            self.ent_pseudo.config(state=tk.DISABLED)
            self.btn_start.pack_forget();
            self.btn_stop.pack(fill="x", ipady=8)
        else:
            self.ent_lineup.config(state=tk.NORMAL);
            self.ent_pseudo.config(state=tk.NORMAL)
            self.btn_stop.pack_forget();
            self.btn_start.pack(fill="x", ipady=8)
            self.btn_start.config(state=tk.NORMAL, text="CONNEXION AU CLOUD")

    def on_stop(self):
        self.btn_stop.config(text="ARRÊT...", state=tk.DISABLED)
        threading.Thread(target=self._async_stop_process, daemon=True).start()

    def _async_stop_process(self):
        try:
            self.logic.stop()
        except:
            pass
        finally:
            self.root.after(0, lambda: self._activate_ui(False))
            self.root.after(0, lambda: self.log("✅ Déconnecté."))


if __name__ == "__main__":
    try:
        check_and_update()
    except:
        pass
    root = tk.Tk()
    app = BridgeApp(root)
    root.mainloop()