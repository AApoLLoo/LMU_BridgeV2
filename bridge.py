import customtkinter as ctk
import threading
import time
import sys
import os
import logging
import requests
from tkinter import scrolledtext
from update import check_and_update
from version import __version__

# --- CONFIGURATION DU CHEMIN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# --- IMPORTS LOGIQUES ---
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

# --- CONFIGURATION DESIGN ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg": "#0B0F19",
    "card": "#151B2B",
    "accent": "#6366F1",
    "accent_hover": "#4F46E5",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "debug": "#A855F7",
    "text": "#F8FAFC",
    "text_dim": "#64748B"
}

VPS_URL = "https://api.racetelemetrybyfbt.com"


def normalize_id(name):
    import re
    safe = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()
    return safe


class MockParentAPI:
    def __init__(self):
        self.identifier = "LMU"
        self.isActive = True


# --- LOGIQUE MÉTIER ---

class ConsumptionTracker:
    def __init__(self, log_func):
        self.log = log_func;
        self.reset()

    def reset(self):
        self.last_lap = -1;
        self.fuel_start = -1.0;
        self.ve_start = -1.0
        self.fuel_last = 0.0;
        self.fuel_avg = 0.0;
        self.fuel_samples = 0
        self.ve_last = 0.0;
        self.ve_avg = 0.0;
        self.ve_samples = 0

    def update(self, current_lap, current_fuel, current_ve, in_pits):
        if self.last_lap == -1 or current_lap < self.last_lap:
            self.last_lap = current_lap;
            self.fuel_start = current_fuel;
            self.ve_start = current_ve
            return
        if current_lap > self.last_lap:
            fuel_delta = self.fuel_start - current_fuel
            ve_delta = self.ve_start - current_ve
            if not in_pits and fuel_delta > 0.01:
                self.fuel_last = fuel_delta;
                self.fuel_samples += 1
                self.fuel_avg = self.fuel_avg + (fuel_delta - self.fuel_avg) / self.fuel_samples
                self.log(f"🏁 Tour {self.last_lap} terminé | Conso: {fuel_delta:.2f}L")
                if ve_delta > 0.01:
                    self.ve_last = ve_delta;
                    self.ve_samples += 1
                    self.ve_avg = self.ve_avg + (ve_delta - self.ve_avg) / self.ve_samples
            self.last_lap = current_lap;
            self.fuel_start = current_fuel;
            self.ve_start = current_ve

    def get_stats(self):
        return {"lastLapFuelConsumption": round(self.fuel_last, 2), "averageConsumptionFuel": round(self.fuel_avg, 2),
                "lastLapVEConsumption": round(self.ve_last, 2), "averageConsumptionVE": round(self.ve_avg, 2)}


class TelemetryRecorder:
    def __init__(self, api_url, team_id):
        self.api_url = api_url;
        self.team_id = team_id;
        self.buffer = [];
        self.current_lap = -1;
        self.driver_name = "Unknown";
        self.track_name = "Unknown";
        self.last_dist = -1

    def update(self, lap_number, vehicle_idx, telemetry, vehicle, scoring):
        if self.current_lap != -1 and lap_number > self.current_lap:
            last_lap_time = 0
            if hasattr(scoring, 'get_vehicle_scoring'):
                for _ in range(10):
                    v_data = scoring.get_vehicle_scoring(vehicle_idx)
                    laps_completed = v_data.get('laps', -1)
                    t_time = v_data.get('last_lap', 0)
                    if laps_completed >= self.current_lap and t_time > 0:
                        last_lap_time = t_time;
                        break
                    time.sleep(0.05)
            self.flush_lap(self.current_lap, last_lap_time)
            self.buffer = [];
            self.last_dist = -1

        self.current_lap = lap_number
        dist = 0
        if hasattr(telemetry, 'lap_distance'): dist = telemetry.lap_distance(vehicle_idx)
        if (dist == 0 or dist is None) and hasattr(scoring, 'get_vehicle_scoring'):
            v_data = scoring.get_vehicle_scoring(vehicle_idx);
            dist = v_data.get('lap_dist', 0)

        if vehicle.speed(vehicle_idx) > 1:
            if self.last_dist == -1 or abs(dist - self.last_dist) > 2.0:
                self.buffer.append({
                    "d": round(dist, 1), "s": round(vehicle.speed(vehicle_idx), 1),
                    "t": round(telemetry.input_throttle(vehicle_idx) * 100, 0),
                    "b": round(telemetry.input_brake(vehicle_idx) * 100, 0),
                    "g": telemetry.gear(vehicle_idx),
                    "ut": round(telemetry.unfiltered_throttle(vehicle_idx) * 100, 0),
                    "ub": round(telemetry.unfiltered_brake(vehicle_idx) * 100, 0),
                    "uc": round(telemetry.unfiltered_clutch(vehicle_idx) * 100, 0),
                    "w": round(telemetry.input_steering(vehicle_idx), 2),
                    "f": round(telemetry.fuel_level(vehicle_idx), 2),
                    "r": round(telemetry.rpm(vehicle_idx), 0),
                    "ve": round(telemetry.virtual_energy(vehicle_idx), 1),
                    "tw": round(telemetry.tire_wear(vehicle_idx)[0], 1),
                    "drag": round(telemetry.drag(vehicle_idx), 1),
                    "df_f": round(telemetry.downforce_front(vehicle_idx), 1),
                    "df_r": round(telemetry.downforce_rear(vehicle_idx), 1),
                    "susp_def": [round(x, 4) for x in telemetry.suspension_deflection(vehicle_idx)],
                    "rh": [round(x, 4) for x in telemetry.ride_height(vehicle_idx)],
                    "susp_f": [round(x, 0) for x in telemetry.suspension_force(vehicle_idx)],
                    "brk_tmp": [round(x, 1) for x in telemetry.brake_temp(vehicle_idx)],
                    "brk_prs": [round(x, 3) for x in telemetry.brake_pressure_list(vehicle_idx)],
                    "lat_f": [round(x, 0) for x in telemetry.lateral_force(vehicle_idx)],
                    "long_f": [round(x, 0) for x in telemetry.longitudinal_force(vehicle_idx)],
                    "t_load": [round(x, 0) for x in telemetry.tire_load(vehicle_idx)],
                    "t_temp_c": [round(x, 1) for x in telemetry.tire_carcass_temp(vehicle_idx)],
                    "t_temp_i": [round(x, 1) for x in telemetry.tire_inner_layer_temp(vehicle_idx)]
                })
                self.last_dist = dist

    def flush_lap(self, lap_num, lap_time):
        if not self.buffer or len(self.buffer) < 50: return
        payload = {"sessionId": self.team_id, "lapNumber": lap_num, "driver": self.driver_name, "lapTime": lap_time,
                   "samples": self.buffer}

        def send():
            try:
                requests.post(f"{self.api_url}/api/telemetry/lap", json=payload,
                              headers={"Content-Type": "application/json"}, timeout=5)
            except:
                pass

        threading.Thread(target=send, daemon=True).start()


class BridgeLogic:
    def __init__(self, log_callback, status_callback):
        self.log = log_callback;
        self.set_status = status_callback
        self.running = False;
        self.debug_mode = False;
        self.connector = None;
        self.rf2_info = None;
        self.rest_info = None;
        self.thread = None;
        self.line_up_name = "";
        self.team_id = "";
        self.driver_pseudo = "";
        self.password = ""
        self.tracker = ConsumptionTracker(self.log);
        self.session_id = 0;
        self.recorder = None;
        self.analysis_enabled = False

    def set_debug(self, enabled):
        self.debug_mode = enabled
        self.log(f"🔧 Mode Debug : {'ACTIVÉ' if enabled else 'DÉSACTIVÉ'}")

    def connect_vps(self, username, password):
        if self.connector: self.connector.disconnect()
        try:
            self.connector = SocketConnector(VPS_URL, port=None, username=username, password=password)
            self.connector.connect()
            time.sleep(2)
            if self.connector.is_connected:
                return True
            else:
                self.log("❌ Échec Authentification (Check Logs)")
                return False
        except Exception as e:
            self.log(f"❌ Erreur VPS: {e}")
            return False

    def start_loop(self, line_up_name, driver_pseudo, password, analysis_enabled):
        self.session_id += 1;
        current_session_id = self.session_id
        self.line_up_name = line_up_name;
        self.team_id = normalize_id(line_up_name);
        self.driver_pseudo = driver_pseudo
        self.password = password
        self.analysis_enabled = analysis_enabled;
        self.running = True;
        self.tracker.reset()

        self.log(f"📊 Analyse : {'ON' if analysis_enabled else 'OFF'}")
        self.thread = threading.Thread(target=self._run, args=(current_session_id,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False;
        self.session_id += 1
        try:
            if self.rf2_info: self.rf2_info.stop()
            if self.rest_info: self.rest_info.stop()
            if self.connector: self.connector.disconnect()
        except:
            pass
        self.rf2_info = None;
        self.rest_info = None;
        self.thread = None
        self.set_status("OFFLINE", COLORS["text_dim"])
        self.log("⏹️ Bridge arrêté.")

    def _run(self, my_session_id):
        self.log("🚀 En attente du jeu...");
        self.set_status("WAITING GAME...", COLORS["warning"])
        pit_strategy = PitStrategyData(port=6397);
        mock_parent = MockParentAPI();
        self.rest_info = RestAPIInfo(mock_parent)

        # CONFIGURATION RESTAPI COMPLÈTE
        self.rest_info.setConnection({
            "url_host": "localhost",
            "url_port_lmu": 6397,
            "connection_timeout": 1.0,
            "connection_retry": 3,
            "connection_retry_delay": 2,
            "restapi_update_interval": 50,  # Intervalle requis
            "enable_restapi_access": True,
            "enable_weather_info": True,
            "enable_session_info": True,
            "enable_garage_setup_info": True,
            "enable_vehicle_info": True,
            "enable_energy_remaining": True
        })

        telemetry = scoring = rules = extended = pit_info = weather = vehicle_helper = None
        last_game_check = 0;
        last_update_time = 0;
        UPDATE_RATE = 0.05;
        last_session_type = -1
        current_history_id = f"{self.team_id}_WAITING";
        self.recorder = TelemetryRecorder(VPS_URL, current_history_id)
        vehicle_trackers = {}

        while self.running:
            if self.session_id != my_session_id: break
            current_time = time.time()

            if self.rf2_info is None:
                if not self.running: break
                if current_time - last_game_check > 5.0:
                    try:
                        self.rf2_info = RF2Info();
                        self.rf2_info.start();
                        self.rest_info.start()
                        self.log("🎮 Jeu connecté !");
                        self.set_status("CONNECTED", COLORS["success"])

                        # INSTANCIATION DES MODULES
                        telemetry = TelemetryData(self.rf2_info, self.rest_info);
                        scoring = ScoringData(self.rf2_info)
                        rules = RulesData(self.rf2_info);
                        extended = ExtendedData(self.rf2_info);
                        pit_info = PitInfoData(self.rf2_info);

                        # === CORRECTION MÉTÉO ICI ===
                        # On passe bien self.rest_info pour que weather.forecast() fonctionne
                        weather = WeatherData(self.rf2_info, self.rest_info);
                        # ============================

                        vehicle_helper = Vehicle(self.rf2_info);
                        self.tracker.reset();
                        vehicle_trackers = {}
                    except:
                        self.rf2_info = None
                    last_game_check = current_time
                time.sleep(0.1);
                continue

            try:
                if not self.running: break
                status = vehicle_helper.get_local_driver_status()
                current_sess_name = "TEST";
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

                        if current_sess_type != last_session_type:
                            current_history_id = f"{self.team_id}_{current_sess_name}_{int(time.time())}"
                            self.log(f"🏁 Session : {current_sess_name}")
                            if self.recorder: self.recorder.team_id = current_history_id
                            vehicle_trackers = {}
                            if self.analysis_enabled:
                                try:
                                    requests.post(f"{VPS_URL}/api/sessions/start",
                                                  json={"sessionId": current_history_id,
                                                        "driver": status.get('driver_name', self.driver_pseudo),
                                                        "circuit": scoring.track_name() if scoring else "Unknown"},
                                                  timeout=2)
                                except:
                                    pass
                            last_session_type = current_sess_type
                    except:
                        pass

                if self.rf2_info and scoring:
                    self.recorder.driver_name = status.get('driver_name', 'Unknown')
                    self.recorder.track_name = scoring.track_name() if scoring else "Unknown"

                if status['is_driving'] and (current_time - last_update_time > UPDATE_RATE):
                    idx = status['vehicle_index'];
                    game_driver = status['driver_name']
                    curr_fuel = telemetry.fuel_level(idx);
                    curr_ve = telemetry.virtual_energy(idx);
                    curr_lap = telemetry.lap_number(idx)
                    try:
                        if self.analysis_enabled: self.recorder.update(curr_lap, idx, telemetry, vehicle_helper,
                                                                       scoring)
                    except Exception as e:
                        self.log(f"ERREUR RECORDER: {e}")

                    # MÉTÉO
                    forecast_data = []
                    try:
                        if hasattr(weather, 'forecast'):
                            raw_f = weather.forecast();
                            k = 'race'
                            if current_sess_type < 5:
                                k = 'practice'
                            elif current_sess_type < 9:
                                k = 'qualify'

                            # DEBUG
                            if self.debug_mode and not raw_f:
                                self.log(f"⚠️ Météo vide. Vérifiez l'API REST.")

                            for node in raw_f.get(k, []):
                                forecast_data.append({"rain": float(node.get("rain_chance", 0.0)) / 100.0,
                                                      "cloud": min(max(float(node.get("sky", 0)), 0) / 4.0, 1.0),
                                                      "temp": float(node.get("temp", 0.0))})
                    except Exception as e:
                        if self.debug_mode: self.log(f"Erreur Météo: {e}")

                    try:
                        scor_veh = scoring.get_vehicle_scoring(idx); in_pits = (scor_veh.get('in_pits', 0) == 1)
                    except:
                        in_pits = False
                    self.tracker.update(curr_lap, curr_fuel, curr_ve, in_pits);
                    stats = self.tracker.get_stats()

                    # TEMPÉRATURES
                    oil_t = 0.0
                    water_t = 0.0
                    try:
                        oil_t = telemetry.temp_oil(idx)
                        water_t = telemetry.temp_water(idx)
                    except:
                        pass

                    all_vehicles = []
                    try:
                        for i in range(scoring.vehicle_count()):
                            v = scoring.get_vehicle_scoring(i);
                            vid = v.get('id');
                            v_pit = (v.get('in_pits') == 1);
                            v_laps = v.get('laps', 0);
                            pit_c = v.get('pit_stops', 0)
                            if vid not in vehicle_trackers: vehicle_trackers[vid] = {
                                'last_pit_lap': v_laps if v_laps > 0 else 0, 'was_in_pits': v_pit, 'pit_count': pit_c}
                            tr = vehicle_trackers[vid]
                            if not tr['was_in_pits'] and v_pit: tr['pit_count'] += 1
                            if tr['was_in_pits'] and not v_pit: tr['last_pit_lap'] = v_laps
                            tr['was_in_pits'] = v_pit
                            if pit_c > tr['pit_count']: tr['pit_count'] = pit_c
                            if tr['last_pit_lap'] > v_laps: tr['last_pit_lap'] = 0
                            v['stint_laps'] = max(0, v_laps - tr['last_pit_lap']);
                            v['pit_stops'] = tr['pit_count']
                            all_vehicles.append(v)
                    except:
                        pass

                    leader = next((v for v in all_vehicles if v['position'] == 1), None);
                    l_laps = leader['laps'] if leader else 0
                    time_info = scoring.time_info();
                    time_info['session'] = current_sess_name
                    elapsed = time_info.get("current", 0);
                    l_avg = 0
                    if l_laps > 0 and elapsed > 0: l_avg = elapsed / l_laps

                    my_pos = scor_veh.get('position', 0);
                    my_cls = scor_veh.get('class', '')
                    c_vehs = [v for v in all_vehicles if v.get('class') == my_cls]
                    c_vehs.sort(key=lambda x: x.get('position', 999))
                    for i, v in enumerate(c_vehs):
                        if v['id'] == scor_veh.get('id'): my_pos = i + 1; break
                    scor_veh['classPosition'] = my_pos

                    payload = {
                        "teamId": self.team_id, "driverName": game_driver, "activeDriverId": self.driver_pseudo,
                        "lastLapFuelConsumption": stats["lastLapFuelConsumption"],
                        "averageConsumptionFuel": stats["averageConsumptionFuel"],
                        "lastLapVEConsumption": stats["lastLapVEConsumption"],
                        "averageConsumptionVE": stats["averageConsumptionVE"],
                        "sessionTimeRemainingSeconds": max(0, time_info.get("end", 0) - time_info.get("current", 0)),
                        "weatherForecast": forecast_data,
                        "telemetry": {
                            "gear": telemetry.gear(idx), "rpm": telemetry.rpm(idx), "speed": vehicle_helper.speed(idx),
                            "fuel": curr_fuel, "fuelCapacity": telemetry.fuel_capacity(idx),
                            "inputs": {"thr": telemetry.input_throttle(idx), "brk": telemetry.input_brake(idx),
                                       "clt": telemetry.input_clutch(idx), "str": telemetry.input_steering(idx)},
                            "temps": {"oil": oil_t, "water": water_t},
                            "tires": {"temp": telemetry.tire_temps(idx), "press": telemetry.tire_pressure(idx),
                                      "wear": telemetry.tire_wear(idx), "brake_wear": telemetry.brake_wear(idx),
                                      "type": telemetry.surface_type(idx), "brake_temp": telemetry.brake_temp(idx),
                                      "compounds": telemetry.tire_compound_name(idx)},
                            "electric": telemetry.electric_data(idx), "virtual_energy": curr_ve,
                            "max_virtual_energy": 100.0,
                            "leaderLaps": l_laps, "leaderAvgLapTime": l_avg, "position": my_pos,
                            "lastLap": telemetry.id(idx)
                        },
                        "scoring": {"track": scoring.track_name(), "time": time_info, "flags": scoring.flag_state(),
                                    "weather": scoring.weather_env(), "vehicles": all_vehicles,
                                    "vehicle_data": scor_veh, "length": scoring.track_length()},
                        "rules": {"sc": rules.sc_info(), "yellow": rules.yellow_flag(),
                                  "my_status": rules.participant_status(idx)},
                        "pit": {"menu": pit_info.menu_status(), "strategy": pit_strategy.pit_estimate()},
                        "weather_det": weather.info(),
                        "extended": {"physics": extended.physics_options(), "pit_limit": extended.pit_limit()}
                    }

                    if self.running and self.session_id == my_session_id:
                        if self.connector: self.connector.send_data(payload)
                        last_update_time = current_time
                        self.set_status(f"LIVE | POS: P{my_pos} | DRIVER: {game_driver}", COLORS["accent"])
                        if self.debug_mode and (oil_t == 0 or water_t == 0):
                            # On loggue une fois toutes les 5 secondes pour ne pas spammer
                            if int(time.time()) % 5 == 0:
                                self.log(f"🔍 DEBUG TEMP: Huile={oil_t}, Eau={water_t}, RPM={telemetry.rpm(idx)}")
                elif not status['is_driving']:
                    self.set_status("EN ATTENTE (PIT / SPECTATE)", COLORS["text_dim"]);
                    time.sleep(0.5)

            except Exception as e:
                if self.running and self.session_id == my_session_id:
                    self.log(f"⚠️ Erreur: {e}");
                    time.sleep(1.0)
                    try:
                        if self.rf2_info: self.rf2_info.stop()
                    except:
                        pass
                    self.rf2_info = None;
                    self.set_status("RECONNECTING...", COLORS["warning"])
                else:
                    break
            time.sleep(0.01)


# --- INTERFACE GRAPHIQUE ---

class BridgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"LMU Bridge {__version__}")
        self.geometry("450x700")
        self.resizable(False, False)

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(30, 20))
        self.lbl_title = ctk.CTkLabel(self.header_frame, text="FBT RACING", font=("Montserrat", 32, "bold"))
        self.lbl_title.pack()
        self.lbl_subtitle = ctk.CTkLabel(self.header_frame, text="SECURE TELEMETRY BRIDGE", font=("Roboto", 12, "bold"),
                                         text_color=COLORS["accent"])
        self.lbl_subtitle.pack(pady=(0, 10))

        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=15)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # ID LineUp
        self.ent_lineup = ctk.CTkEntry(self.main_frame, placeholder_text="ID LineUp (Nom Team)", height=45,
                                       border_width=0, fg_color=COLORS["bg"])
        self.ent_lineup.pack(fill="x", padx=20, pady=(20, 10))

        # Pseudo Pilote
        self.ent_pseudo = ctk.CTkEntry(self.main_frame, placeholder_text="Votre Pseudo (Compte)", height=45,
                                       border_width=0, fg_color=COLORS["bg"])
        self.ent_pseudo.pack(fill="x", padx=20, pady=(0, 10))

        # Mot de passe (NOUVEAU)
        self.ent_password = ctk.CTkEntry(self.main_frame, placeholder_text="Mot de passe Compte", height=45,
                                         border_width=0, fg_color=COLORS["bg"], show="*")
        self.ent_password.pack(fill="x", padx=20, pady=(0, 20))

        self.sw_analysis = ctk.CTkSwitch(self.main_frame, text="ENREGISTRER POUR ANALYSE",
                                         progress_color=COLORS["success"])
        self.sw_analysis.pack(pady=5)
        self.sw_debug = ctk.CTkSwitch(self.main_frame, text="MODE DEBUG (LOGS)", progress_color=COLORS["debug"],
                                      command=self.toggle_debug)
        self.sw_debug.pack(pady=5)

        self.btn_start = ctk.CTkButton(self.main_frame, text="CONNEXION & START", height=50,
                                       font=("Segoe UI", 14, "bold"), fg_color=COLORS["accent"],
                                       hover_color=COLORS["accent_hover"], command=self.on_start)
        self.btn_start.pack(fill="x", padx=20, pady=(20, 10))

        self.btn_stop = ctk.CTkButton(self.main_frame, text="DÉCONNEXION", height=40, font=("Segoe UI", 12, "bold"),
                                      fg_color=COLORS["danger"], hover_color="#DC2626", command=self.on_stop)

        self.lbl_status = ctk.CTkLabel(self, text="LOGIN REQUIRED", font=("Consolas", 12, "bold"),
                                       text_color=COLORS["text_dim"])
        self.lbl_status.pack(side="bottom", pady=10)

        self.log_textbox = ctk.CTkTextbox(self.main_frame, height=150, fg_color="#000000", text_color="#4ADE80",
                                          font=("Consolas", 10))
        self.log_textbox.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        self.log_textbox.configure(state="disabled")

        self.logic = BridgeLogic(self.log_message, self.set_status_text)

    def toggle_debug(self):
        self.logic.set_debug(self.sw_debug.get() == 1)

    def log_message(self, msg):
        self.after(0, lambda: self._log_safe(msg))

    def _log_safe(self, msg):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"> {msg}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def set_status_text(self, text, color):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

    def on_start(self):
        l = self.ent_lineup.get().strip()
        p = self.ent_pseudo.get().strip()
        pwd = self.ent_password.get().strip()

        if not l or not p or not pwd:
            self.lbl_status.configure(text="CHAMPS REQUIS (ID, Pseudo, MDP) !", text_color=COLORS["warning"])
            return

        self.btn_start.pack_forget()
        self.btn_stop.pack(fill="x", padx=20, pady=(20, 10))
        self.ent_lineup.configure(state="disabled")
        self.ent_pseudo.configure(state="disabled")
        self.ent_password.configure(state="disabled")

        threading.Thread(target=self._check_and_start, args=(l, p, pwd, self.sw_analysis.get() == 1)).start()

    def _check_and_start(self, l, p, pwd, ana):
        self.log_message("🔐 Authentification...")
        if self.logic.connect_vps(p, pwd):
            self.log_message("✅ IDENTIFICATION OK")
            self.logic.start_loop(l, p, pwd, ana)
        else:
            self.log_message("❌ ÉCHEC AUTHENTIFICATION")
            self.after(0, self.reset_ui)

    def on_stop(self):
        self.btn_stop.configure(text="ARRET EN COURS...", state="disabled")
        threading.Thread(target=self._async_stop).start()

    def _async_stop(self):
        self.logic.stop()
        self.after(0, self.reset_ui)

    def reset_ui(self):
        self.btn_stop.pack_forget()
        self.btn_stop.configure(text="DÉCONNEXION", state="normal")
        self.btn_start.pack(fill="x", padx=20, pady=(20, 10))
        self.ent_lineup.configure(state="normal")
        self.ent_pseudo.configure(state="normal")
        self.ent_password.configure(state="normal")
        self.log_message("--- SESSION TERMINÉE ---")


if __name__ == "__main__":
    try:
        check_and_update()
    except:
        pass
    app = BridgeApp()
    app.mainloop()