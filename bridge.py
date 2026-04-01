import customtkinter as ctk
import threading
import time
import sys
import os
import json
import logging
import requests
from datetime import datetime
from tkinter import scrolledtext
from update import check_and_update
from version_manager import get_version_manager
from tls_config import bootstrap_tls_env

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
    "bg": "#0A0E1A",
    "bg_gradient": "#151B2E",
    "card": "#1A2336",
    "card_hover": "#212E47",
    "accent": "#6366F1",
    "accent_hover": "#4F46E5",
    "accent_light": "#818CF8",
    "success": "#10B981",
    "success_hover": "#059669",
    "danger": "#EF4444",
    "danger_hover": "#DC2626",
    "warning": "#F59E0B",
    "warning_hover": "#D97706",
    "debug": "#A855F7",
    "debug_hover": "#9333EA",
    "text": "#F8FAFC",
    "text_dim": "#64748B",
    "text_subdim": "#475569",
    "border": "#334155"
}

VPS_URL = "https://api.racetelemetrybyfbt.com"
CONFIG_PATH = os.path.join(current_dir, "config.json")


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(
    lineup_id: str,
    pseudo: str,
    password: str = "",
    save_password: bool = False,
    window_geometry: str = "",
) -> None:
    try:
        # Préserve les clés existantes (ex: géométrie) lors d'une sauvegarde partielle.
        config_data = load_config()
        config_data["lineup_id"] = lineup_id
        config_data["pseudo"] = pseudo

        if save_password and password:
            config_data["password"] = password
        else:
            config_data.pop("password", None)

        if window_geometry:
            config_data["window_geometry"] = window_geometry

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f)
    except Exception:
        pass


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
        self.last_dist = -1;
        self.lap_start_fuel = 0.0;
        self.lap_start_ve = 0.0;
        self.lap_samples_count = 0;
        self.lap_speed_sum = 0.0

    def update(self, lap_number, vehicle_idx, telemetry, vehicle, scoring):
        # === DÉTECTION TRANSITION ENTRE LAPS ===
        if self.current_lap != -1 and lap_number > self.current_lap:
            last_lap_time = 0
            lap_invalidated = False
            lap_weather = {}

            if hasattr(scoring, 'get_vehicle_scoring'):
                for _ in range(10):
                    v_data = scoring.get_vehicle_scoring(vehicle_idx)
                    laps_completed = v_data.get('laps', -1)
                    t_time = v_data.get('last_lap', 0)
                    if laps_completed >= self.current_lap and t_time > 0:
                        last_lap_time = t_time;
                        break
                    time.sleep(0.05)

            # Récupère infos LMU sur invalidation
            try:
                lmu_extra = telemetry.lmu_extra_telemetry(vehicle_idx)
                lap_invalidated = lmu_extra.get('lap_invalidated', False)
            except:
                lap_invalidated = False

            # Récupère météo
            try:
                lap_weather = scoring.weather_env()
            except:
                lap_weather = {}

            self.flush_lap(self.current_lap, last_lap_time, lap_invalidated, lap_weather)
            self.buffer = [];
            self.last_dist = -1
            self.lap_samples_count = 0
            self.lap_speed_sum = 0.0

        self.current_lap = lap_number

        # === RÉCUPÈRE INFOS LAP ET POSITION ===
        dist = 0
        try:
            if hasattr(telemetry, 'lap_distance'):
                dist = telemetry.lap_distance(vehicle_idx)
        except:
            pass

        if (dist == 0 or dist is None) and hasattr(scoring, 'get_vehicle_scoring'):
            try:
                v_data = scoring.get_vehicle_scoring(vehicle_idx);
                dist = v_data.get('lap_dist', 0)
                in_pits = v_data.get('in_pits', 0) == 1
            except:
                in_pits = False
        else:
            in_pits = False

        # === POSITION XZ POUR TRACK MAP ===
        try:
            scor_veh = scoring.get_vehicle_scoring(vehicle_idx)
            pos_x = scor_veh.get('x', 0.0)
            pos_z = scor_veh.get('z', 0.0)
        except:
            pos_x, pos_z = 0.0, 0.0

        # === CONDITIONS RECORDING ===
        speed = vehicle.speed(vehicle_idx)
        steering = abs(telemetry.input_steering(vehicle_idx))

        # Seuil de sampling adaptatif: plus fin en virage (steering > 0.15)
        sampling_threshold = 0.5 if steering > 0.15 else 2.0

        # Valide que vitesse > 5 km/h et pas en pits
        if speed > 5 and not in_pits:
            if self.last_dist == -1 or abs(dist - self.last_dist) > sampling_threshold:
                self.buffer.append({
                    "d": round(dist, 1), "s": round(speed, 1),
                    "x": round(pos_x, 1), "z": round(pos_z, 1),
                    "t": round(telemetry.input_throttle(vehicle_idx) * 100, 0),
                    "b": round(telemetry.input_brake(vehicle_idx) * 100, 0),
                    "g": telemetry.gear(vehicle_idx),
                    "ut": round(telemetry.unfiltered_throttle(vehicle_idx) * 100, 0),
                    "ub": round(telemetry.unfiltered_brake(vehicle_idx) * 100, 0),
                    "uc": round(telemetry.unfiltered_clutch(vehicle_idx) * 100, 0),
                    "w": round(steering, 2),
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
                self.lap_samples_count += 1
                self.lap_speed_sum += speed
                if len(self.buffer) > 5000:
                    self.buffer = self.buffer[-5000:]

    def flush_lap(self, lap_num, lap_time, lap_invalidated=False, lap_weather=None):
        if not self.buffer or len(self.buffer) < 50: return

        avg_speed = self.lap_speed_sum / self.lap_samples_count if self.lap_samples_count > 0 else 0.0

        payload = {
            "sessionId": self.team_id,
            "lapNumber": lap_num,
            "driver": self.driver_name,
            "lapTime": lap_time,
            "invalidated": lap_invalidated,
            "avgSpeed": round(avg_speed, 1),
            "samplesCount": self.lap_samples_count,
            "weather": lap_weather if lap_weather else {},
            "samples": self.buffer
        }

        def send():
            try:
                requests.post(f"{self.api_url}/api/telemetry/lap", json=payload,
                              headers={"Content-Type": "application/json"}, timeout=5)
            except:
                pass

        threading.Thread(target=send, daemon=True).start()


class BridgeLogic:
    def __init__(self, log_callback, status_callback, vps_status_callback=None):
        self.log = log_callback
        bootstrap_tls_env(self.log)
        self.set_status = status_callback
        self.set_vps_status = vps_status_callback if vps_status_callback else status_callback
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
            self.set_vps_status("CONNEXION...", COLORS["warning"])
            self.connector = SocketConnector(VPS_URL, port=None, username=username, password=password, log_callback=self.log)
            self.connector.connect()
            time.sleep(2)
            if self.connector.is_connected:
                self.set_vps_status("CONNECTÉ", COLORS["success"])
                return True
            else:
                self.log("❌ Échec Authentification (Check Logs)")
                self.set_vps_status("OFFLINE", COLORS["danger"])
                return False
        except Exception as e:
            self.log(f"❌ Erreur VPS: {e}")
            self.set_vps_status("OFFLINE", COLORS["danger"])
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
        self.rf2_info = None
        self.rest_info = None
        self.thread = None
        self.set_status("OFFLINE", COLORS["text_dim"])
        self.set_vps_status("OFFLINE", COLORS["text_dim"])
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
        last_presence_time = 0;
        UPDATE_RATE = 0.05;
        PRESENCE_RATE = 1.0;
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
                        weather = WeatherData(self.rf2_info, self.rest_info);
                        vehicle_helper = Vehicle(self.rf2_info);
                        self.tracker.reset();
                        vehicle_trackers = {}
                    except Exception as e:
                        self.log(f"❌ Erreur connexion jeu: {e}")
                        self.rf2_info = None
                    last_game_check = current_time
                time.sleep(0.1);
                continue

            try:
                if not self.running: break
                status = vehicle_helper.get_local_driver_status()
                idx = status.get('vehicle_index', -1)
                current_sess_name = "TEST";
                current_sess_type = 0

                # Présence: on garde la visibilité des connectés même sans roulage.
                if current_time - last_presence_time > PRESENCE_RATE:
                    driver_state = "CONNECTED_IDLE"
                    if status.get('is_driving'):
                        driver_state = "CONNECTED_DRIVING"
                        try:
                            scor_local = scoring.get_vehicle_scoring(idx) if (scoring and idx >= 0) else {}
                            if scor_local.get('in_pits', 0) == 1:
                                driver_state = "PIT"
                        except:
                            pass
                    elif self.rf2_info and self.rf2_info.isPaused:
                        driver_state = "SPECTATE"

                    presence_payload = {
                        "teamId": self.team_id,
                        "driverId": self.driver_pseudo,
                        "driverName": status.get('driver_name', self.driver_pseudo),
                        "state": driver_state,
                        "isDriving": bool(status.get('is_driving', False)),
                        "vehicleIndex": idx,
                        "session": current_sess_name,
                        "ts": int(current_time * 1000)
                    }
                    if self.connector:
                        self.connector.send_presence(presence_payload)
                    last_presence_time = current_time

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
                                try:
                                    forecast_data.append({
                                        "rain": float(node.get("rain_chance", 0.0)) / 100.0,
                                        "cloud": min(max(float(node.get("sky", 0)), 0) / 4.0, 1.0),
                                        "temp": float(node.get("temp", 0.0))
                                    })
                                except (TypeError, ValueError):
                                    continue
                    except Exception as e:
                        if self.debug_mode: self.log(f"Erreur Météo: {e}")

                    scor_veh = {}
                    try:
                        scor_veh = scoring.get_vehicle_scoring(idx); in_pits = (scor_veh.get('in_pits', 0) == 1)
                    except:
                        in_pits = False
                    try:
                        car_state = telemetry.car_state(idx)
                    except:
                        car_state = {}
                    try:
                        turbo_pressure = telemetry.turbo_pressure(idx)
                    except:
                        turbo_pressure = 0.0
                    try:
                        lv_x, lv_y, lv_z = telemetry.local_velocity(idx)
                    except:
                        lv_x, lv_y, lv_z = 0.0, 0.0, 0.0
                    try:
                        la_x, la_y, la_z = telemetry.local_acceleration(idx)
                    except:
                        la_x, la_y, la_z = 0.0, 0.0, 0.0
                    try:
                        lra_x, lra_y, lra_z = telemetry.local_rot_acceleration(idx)
                    except:
                        lra_x, lra_y, lra_z = 0.0, 0.0, 0.0
                    try:
                        engine_torque = telemetry.engine_torque(idx)
                    except:
                        engine_torque = 0.0
                    try:
                        steering_shaft_torque = telemetry.steering_shaft_torque(idx)
                    except:
                        steering_shaft_torque = 0.0
                    try:
                        rest_tlm = self.rest_info.telemetry if self.rest_info else None
                        rest_api_data = {
                            "time_scale": getattr(rest_tlm, "timeScale", 1),
                            "track_clock_time": getattr(rest_tlm, "trackClockTime", -1.0),
                            "private_qualifying": getattr(rest_tlm, "privateQualifying", 0),
                            "steering_wheel_range": getattr(rest_tlm, "steeringWheelRange", 0.0),
                            "current_virtual_energy": getattr(rest_tlm, "currentVirtualEnergy", 0.0),
                            "max_virtual_energy": getattr(rest_tlm, "maxVirtualEnergy", 0.0),
                            "expected_fuel_consumption": getattr(rest_tlm, "expectedFuelConsumption", 0.0),
                            "expected_virtual_energy_consumption": getattr(rest_tlm, "expectedVirtualEnergyConsumption", 0.0),
                            "aero_damage": getattr(rest_tlm, "aeroDamage", -1.0),
                            "penalty_time": getattr(rest_tlm, "penaltyTime", 0.0),
                            "suspension_damage": getattr(rest_tlm, "suspensionDamage", (0.0, 0.0, 0.0, 0.0)),
                            "stint_usage": getattr(rest_tlm, "stintUsage", {}),
                            "pit_stop_estimate": getattr(rest_tlm, "pitStopEstimate", (0.0, 0.0, 0.0, 0.0, 0)),
                        }
                    except:
                        rest_api_data = {}
                    try:
                        flats = telemetry.tire_flat(idx)
                    except:
                        flats = [False, False, False, False]
                    try:
                        detached = telemetry.wheel_detached(idx)
                    except:
                        detached = [False, False, False, False]
                    try:
                        dents = telemetry.dents(idx)
                    except:
                        dents = [0, 0, 0, 0, 0, 0, 0, 0]
                    try:
                        overheating = telemetry.overheating(idx)
                    except:
                        overheating = False
                    self.tracker.update(curr_lap, curr_fuel, curr_ve, in_pits);
                    stats = self.tracker.get_stats()

                    oil_t = 0.0
                    water_t = 0.0
                    try:
                        oil_t = telemetry.temp_oil(idx)
                        water_t = telemetry.temp_water(idx)
                    except Exception as e:
                        if int(time.time()) % 5 == 0:
                            print(f"⚠️ Erreur Températures : {e}")
                        pass

                    all_vehicles = []
                    try:
                        for i in range(scoring.vehicle_count()):
                            v = scoring.get_vehicle_scoring(i)
                            vid = v.get('id')
                            if vid is None:
                                continue
                            v_pit = (v.get('in_pits') == 1)
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
                        "restapi": rest_api_data,
                        "telemetry": {
                            "gear": telemetry.gear(idx), "rpm": telemetry.rpm(idx),
                            "speed": vehicle_helper.speed(idx), "maxRpm": telemetry.rpm_max(idx),
                            "fuel": curr_fuel, "fuelCapacity": telemetry.fuel_capacity(idx),
                            "inputs": {"thr": telemetry.input_throttle(idx), "brk": telemetry.input_brake(idx),
                                       "clt": telemetry.input_clutch(idx), "str": telemetry.input_steering(idx)},
                            "brake_bias": car_state.get("brake_bias", 0.0),
                            "car_state": {
                                "speed_limiter": bool(car_state.get("speed_limiter", False)),
                                "headlights": bool(car_state.get("headlights", False)),
                                "ignition": int(car_state.get("ignition", 0)),
                                "drs": bool(car_state.get("drs", False)),
                                "attack_mode": int(car_state.get("attack_mode", 0))
                            },
                            "turbo_pressure": turbo_pressure,
                            "engine_torque": engine_torque,
                            "steering_shaft_torque": steering_shaft_torque,
                            "local_velocity": {"x": lv_x, "y": lv_y, "z": lv_z},
                            "local_acceleration": {"x": la_x, "y": la_y, "z": la_z},
                            "local_rot_acceleration": {"x": lra_x, "y": lra_y, "z": lra_z},
                            "vehicle_health": {
                                "overheating": bool(overheating),
                                "tire_flat_count": sum(1 for x in flats if x),
                                "wheel_detached_count": sum(1 for x in detached if x),
                                "dents_max": max(dents) if dents else 0,
                                "by_wheel": {
                                    "fl": {"flat": bool(flats[0]) if len(flats) > 0 else False,
                                           "detached": bool(detached[0]) if len(detached) > 0 else False},
                                    "fr": {"flat": bool(flats[1]) if len(flats) > 1 else False,
                                           "detached": bool(detached[1]) if len(detached) > 1 else False},
                                    "rl": {"flat": bool(flats[2]) if len(flats) > 2 else False,
                                           "detached": bool(detached[2]) if len(detached) > 2 else False},
                                    "rr": {"flat": bool(flats[3]) if len(flats) > 3 else False,
                                           "detached": bool(detached[3]) if len(detached) > 3 else False}
                                }
                            },
                            "temps": {"oil": oil_t, "water": water_t},
                            "tires": {"temp": telemetry.tire_temps(idx), "press": telemetry.tire_pressure(idx),
                                      "wear": telemetry.tire_wear(idx), "brake_wear": telemetry.brake_wear(idx),
                                      "type": telemetry.surface_type(idx), "brake_temp": telemetry.brake_temp(idx),
                                      "compounds": telemetry.tire_compound_name(idx)},
                            "electric": telemetry.electric_data(idx), "virtual_energy": curr_ve,
                            "max_virtual_energy": 100.0,
                            "lmu_electronics": telemetry.lmu_electronics(idx),
                            "lmu_extra": telemetry.lmu_extra_telemetry(idx),
                            "lmu_wheels_extra": telemetry.lmu_wheels_extra(idx),
                            "leaderLaps": l_laps, "leaderAvgLapTime": l_avg, "position": my_pos,
                            "lastLap": telemetry.id(idx)
                        },
                        "scoring": {"track": scoring.track_name(), "time": time_info, "flags": scoring.flag_state(),
                                    "weather": scoring.weather_env(), "vehicles": all_vehicles,
                                    "vehicle_data": scor_veh, "length": scoring.track_length(),
                                    "lmu_scoring_extra": scoring.lmu_scoring_extra()
                                    # =============================
                                    },
                        "rules": {"sc": rules.sc_info(), "yellow": rules.yellow_flag(),
                                  "my_status": rules.participant_status(idx)},
                        "pit": {"menu": pit_info.menu_status(), "strategy": pit_strategy.pit_estimate()},
                        "weather_det": weather.info(),
                        "extended": {"physics": extended.physics_options(), "pit_limit": extended.pit_limit()}
                    }

                    if self.running and self.session_id == my_session_id:
                        if self.connector: self.connector.send_telemetry(payload)
                        last_update_time = current_time
                        self.set_status(f"LIVE | POS: P{my_pos} | DRIVER: {game_driver}", COLORS["accent"])

                        # --- GESTION DU LOG DEBUG POUR LE PAYLOAD ---
                        if self.debug_mode:
                            # On n'affiche le payload complet que toutes les 3 secondes pour ne pas freezer l'appli
                            if int(current_time) % 3 == 0 and getattr(self, '_last_debug_payload', 0) != int(
                                    current_time):
                                self._last_debug_payload = int(current_time)
                                # Extrait juste les nouvelles données pour le visuel Debug, ou tout le payload si vous préférez :
                                debug_str = json.dumps({
                                    "brake_bias": payload["telemetry"].get("brake_bias"),
                                    "car_state": payload["telemetry"].get("car_state"),
                                    "turbo_pressure": payload["telemetry"].get("turbo_pressure"),
                                    "local_velocity": payload["telemetry"].get("local_velocity"),
                                    "vehicle_health": payload["telemetry"].get("vehicle_health"),
                                    "electronics": payload["telemetry"]["lmu_electronics"],
                                    "lmu_extra": payload["telemetry"]["lmu_extra"],
                                    "scoring_extra": payload["scoring"]["lmu_scoring_extra"],
                                    "lmu_wheels_extra" : payload["telemetry"]["lmu_wheels_extra"],
                                }, indent=2, default=str)
                                self.log(f"📦 [DEBUG PAYLOAD (Nouveautés LMU)]\n{debug_str}")
                elif not status['is_driving']:
                    if self.rf2_info and self.rf2_info.isPaused:
                        self.set_status("PLUGIN INACTIF OU JEU NON ACTIF", COLORS["warning"])
                    else:
                        self.set_status("EN ATTENTE (PIT / SPECTATE)", COLORS["text_dim"])
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
        version_mgr = get_version_manager()
        self.title(f"LMU Bridge {version_mgr.get_current_version()}")
        self.geometry("550x1000")
        self.minsize(500, 760)
        self.resizable(True, True)
        self.configure(fg_color=COLORS["bg"])

        # Restaure taille/position précédente si disponible.
        self._cfg = load_config()
        saved_geometry = self._cfg.get("window_geometry", "")
        if isinstance(saved_geometry, str) and saved_geometry:
            try:
                self.geometry(saved_geometry)
            except Exception:
                pass

        # === HEADER SECTION ===
        self.header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.header_frame.pack(fill="x", padx=0, pady=0)
        
        # Top gradient bar
        self.gradient_bar = ctk.CTkFrame(self.header_frame, fg_color=COLORS["accent"], height=4, corner_radius=0)
        self.gradient_bar.pack(fill="x", pady=0)
        
        # Title & Subtitle
        title_container = ctk.CTkFrame(self.header_frame, fg_color=COLORS["bg"], corner_radius=0)
        title_container.pack(fill="x", padx=0, pady=(25, 5))
        
        self.lbl_title = ctk.CTkLabel(
            title_container,
            text="⚡ FBT RACING",
            font=("Segoe UI", 38, "bold"),
            text_color=COLORS["accent_light"]
        )
        self.lbl_title.pack(pady=0)
        
        self.lbl_subtitle = ctk.CTkLabel(
            title_container,
            text="Secure Telemetry Bridge",
            font=("Segoe UI", 11),
            text_color=COLORS["text_subdim"]
        )
        self.lbl_subtitle.pack(pady=(5, 20))
        
        # === SCROLLABLE MAIN CONTENT ===
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg"],
            corner_radius=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # === CREDENTIALS CARD ===
        self._create_section_header(self.scroll_frame, "📋 IDENTIFIANTS", 20, 15)
        
        self.ent_lineup = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="ID LineUp (Nom Team)",
            height=45,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["card"],
            text_color=COLORS["text"]
        )
        self.ent_lineup.pack(fill="x", padx=20, pady=(10, 8))

        self.ent_pseudo = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="Votre Pseudo (Compte)",
            height=45,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["card"],
            text_color=COLORS["text"]
        )
        self.ent_pseudo.pack(fill="x", padx=20, pady=(0, 8))

        self.ent_password = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="Mot de passe Compte",
            height=45,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["card"],
            text_color=COLORS["text"],
            show="*"
        )
        self.ent_password.pack(fill="x", padx=20, pady=(0, 15))
        
        # === OPTIONS CARD ===
        self._create_section_header(self.scroll_frame, "⚙️ OPTIONS", 20, 15)
        
        options_card = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["card"], corner_radius=12)
        options_card.pack(fill="x", padx=20, pady=(10, 15))
        
        self.sw_save_password = ctk.CTkSwitch(
            options_card,
            text="🔐 Sauvegarder mot de passe",
            progress_color=COLORS["warning"],
            fg_color=COLORS["card_hover"]
        )
        self.sw_save_password.pack(fill="x", padx=15, pady=(12, 8))
        
        self.sw_analysis = ctk.CTkSwitch(
            options_card,
            text="📊 Enregistrer pour analyse",
            progress_color=COLORS["success"],
            fg_color=COLORS["card_hover"]
        )
        self.sw_analysis.pack(fill="x", padx=15, pady=(0, 8))
        
        self.sw_debug = ctk.CTkSwitch(
            options_card,
            text="🔧 Mode debug (logs détaillés)",
            progress_color=COLORS["debug"],
            fg_color=COLORS["card_hover"],
            command=self.toggle_debug
        )
        self.sw_debug.pack(fill="x", padx=15, pady=(0, 12))
        
        # === STATUS INDICATORS ===
        self._create_section_header(self.scroll_frame, "📡 STATUT CONNEXION", 20, 15)
        
        self.game_status_row = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["card"], corner_radius=10, height=50)
        self.game_status_row.pack(fill="x", padx=20, pady=(10, 8))
        
        self.game_dot = ctk.CTkLabel(
            self.game_status_row,
            text="●",
            width=20,
            text_color=COLORS["text_dim"],
            font=("Consolas", 16)
        )
        self.game_dot.pack(side="left", padx=(15, 10), pady=12)
        
        self.game_status_label = ctk.CTkLabel(
            self.game_status_row,
            text="JEU: EN ATTENTE",
            font=("Segoe UI", 11),
            text_color=COLORS["text_dim"],
            anchor="w"
        )
        self.game_status_label.pack(side="left", fill="x", expand=True, padx=(0, 15), pady=12)
        
        self.vps_status_row = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["card"], corner_radius=10, height=50)
        self.vps_status_row.pack(fill="x", padx=20, pady=(0, 15))
        
        self.vps_dot = ctk.CTkLabel(
            self.vps_status_row,
            text="●",
            width=20,
            text_color=COLORS["text_dim"],
            font=("Consolas", 16)
        )
        self.vps_dot.pack(side="left", padx=(15, 10), pady=12)
        
        self.vps_status_label = ctk.CTkLabel(
            self.vps_status_row,
            text="VPS: OFFLINE",
            font=("Segoe UI", 11),
            text_color=COLORS["text_dim"],
            anchor="w"
        )
        self.vps_status_label.pack(side="left", fill="x", expand=True, padx=(0, 15), pady=12)
        
        # === ACTION BUTTONS ===
        self.btn_start = ctk.CTkButton(
            self.scroll_frame,
            text="🚀 CONNEXION & START",
            height=55,
            font=("Segoe UI", 14, "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
            command=self.on_start,
            corner_radius=10
        )
        self.btn_start.pack(fill="x", padx=20, pady=(10, 8))

        self.btn_stop = ctk.CTkButton(
            self.scroll_frame,
            text="⛔ DÉCONNEXION",
            height=55,
            font=("Segoe UI", 14, "bold"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            text_color=COLORS["text"],
            command=self.on_stop,
            corner_radius=10
        )
        
        # === LOGS SECTION ===
        self._create_section_header(self.scroll_frame, "📝 JOURNAL D'ACTIVITÉ", 20, 15)
        
        self.log_header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.log_header_frame.pack(fill="x", padx=20, pady=(0, 8))
        
        self.lbl_log_header = ctk.CTkLabel(
            self.log_header_frame,
            text="",
            font=("Segoe UI", 9),
            text_color=COLORS["text_dim"]
        )
        self.lbl_log_header.pack(side="left")
        
        self.btn_clear_log = ctk.CTkButton(
            self.log_header_frame,
            text="🗑 Effacer",
            width=60,
            height=28,
            font=("Segoe UI", 10),
            fg_color=COLORS["card"],
            hover_color=COLORS["danger"],
            text_color=COLORS["text_dim"],
            command=self._clear_logs,
            corner_radius=6
        )
        self.btn_clear_log.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            self.scroll_frame,
            height=150,
            fg_color="#0F1419",
            text_color="#4ADE80",
            font=("Consolas", 9),
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8
        )
        self.log_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 25))
        self.log_textbox.configure(state="disabled")

        # Initialize logic
        self.logic = BridgeLogic(
            self.log_message,
            self.set_status_text,
            lambda text, color: self.set_status_text(text, color, kind="vps")
        )

        # Load saved config
        _cfg = self._cfg
        if _cfg.get("lineup_id"):
            self.ent_lineup.insert(0, _cfg["lineup_id"])
        if _cfg.get("pseudo"):
            self.ent_pseudo.insert(0, _cfg["pseudo"])
        if _cfg.get("password"):
            self.ent_password.insert(0, _cfg["password"])
            self.sw_save_password.select()

        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _create_section_header(self, parent, title, padx, pady):
        """Helper to create section headers"""
        header = ctk.CTkLabel(
            parent,
            text=title,
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["accent_light"],
            anchor="w"
        )
        header.pack(fill="x", padx=padx, pady=pady)

    def toggle_debug(self):
        self.logic.set_debug(self.sw_debug.get() == 1)

    def log_message(self, msg):
        self.after(0, lambda: self._log_safe(msg))

    def _log_safe(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {msg}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _clear_logs(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def set_status_text(self, text, color, kind="game"):
        def _update():
            if kind == "vps":
                self.vps_dot.configure(text_color=color)
                self.vps_status_label.configure(text=f"VPS: {text}", text_color=color)
            else:
                self.game_dot.configure(text_color=color)
                self.game_status_label.configure(text=f"JEU: {text}", text_color=color)
        self.after(0, _update)

    def _save_window_geometry(self):
        save_config(
            self.ent_lineup.get().strip(),
            self.ent_pseudo.get().strip(),
            self.ent_password.get().strip(),
            self.sw_save_password.get() == 1,
            self.geometry(),
        )

    def _on_window_close(self):
        self._save_window_geometry()
        self.destroy()

    def on_start(self):
        l = self.ent_lineup.get().strip()
        p = self.ent_pseudo.get().strip()
        pwd = self.ent_password.get().strip()

        if not l or not p or not pwd:
            self.game_status_label.configure(text="JEU: CHAMPS REQUIS !", text_color=COLORS["warning"])
            return

        save_password_enabled = self.sw_save_password.get() == 1
        save_config(l, p, pwd, save_password_enabled, self.geometry())
        self.btn_start.pack_forget()
        self.btn_stop.pack(fill="x", padx=20, pady=(10, 8))
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
        self.btn_stop.configure(text="⛔ ARRÊT EN COURS...", state="disabled")
        threading.Thread(target=self._async_stop).start()

    def _async_stop(self):
        self.logic.stop()
        self.after(0, self.reset_ui)

    def reset_ui(self):
        self.btn_stop.pack_forget()
        self.btn_stop.configure(text="⛔ DÉCONNEXION", state="normal")
        self.btn_start.pack(fill="x", padx=20, pady=(10, 8))
        self.ent_lineup.configure(state="normal")
        self.ent_pseudo.configure(state="normal")
        self.ent_password.configure(state="normal")
        self.log_message("--- SESSION TERMINÉE ---")


# --- GESTION DES SETUPS ---

class SetupManager:
    """Manage garage setups and apply them to vehicle"""
    def __init__(self, api_base_url="http://localhost:6397", log_func=None):
        self.api_base_url = api_base_url
        self.log = log_func if log_func else lambda x: None
        self._setups_cache = []
        self._cache_time = 0.0
        self._CACHE_TTL = 5.0  # Refresh setups every 5 sec

    def fetch_setups(self):
        """Récupère liste des setups disponibles depuis l'API garage"""
        now = time.monotonic()
        if now - self._cache_time < self._CACHE_TTL:
            return self._setups_cache

        try:
            url = f"{self.api_base_url}/rest/garage/setups"
            resp = requests.get(url, timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                # Flexibilité sur format: liste directe ou { setups: [...] }
                if isinstance(data, list):
                    self._setups_cache = data
                elif isinstance(data, dict) and "setups" in data:
                    self._setups_cache = data["setups"]
                else:
                    self._setups_cache = []
                self._cache_time = now
                self.log(f"✅ Setups loaded: {len(self._setups_cache)} found")
                return self._setups_cache
        except Exception as e:
            self.log(f"❌ Erreur fetch setups: {e}")

        self._cache_time = now
        return self._setups_cache

    def apply_setup(self, setup_id: str):
        """Applique un setup sur la voiture"""
        try:
            url = f"{self.api_base_url}/rest/garage/setups/apply"
            payload = {"setupId": setup_id}
            resp = requests.post(url, json=payload, timeout=2.0)
            if resp.status_code == 200:
                result = resp.json()
                self.log(f"✅ Setup {setup_id} appliqué")
                return {"success": True, "message": f"Setup {setup_id} loaded", "data": result}
            else:
                self.log(f"⚠️ Setup {setup_id} - HTTP {resp.status_code}")
                return {"success": False, "message": f"HTTP {resp.status_code}", "data": None}
        except Exception as e:
            self.log(f"❌ Erreur apply setup: {e}")
            return {"success": False, "message": str(e), "data": None}

    def get_setup_summary(self):
        """Retourne un résumé compact des setups pour le payload"""
        try:
            setups = self.fetch_setups()
            return {
                "count": len(setups),
                "setups": [
                    {"id": s.get("id", ""), "name": s.get("name", "Unknown")}
                    for s in setups[:20]  # Limite à 20 pour payload compact
                ]
            }
        except:
            return {"count": 0, "setups": []}


if __name__ == "__main__":
    try:
        check_and_update()
    except:
        pass
    app = BridgeApp()
    app.mainloop()

