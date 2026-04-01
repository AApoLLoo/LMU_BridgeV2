"""
LMU API data set - Ported to pyLMUSharedMemory
Optimized for performance and LMU specific data (Battery/Fuel %, DRS)
"""
from __future__ import annotations
import time
import requests
from validator import bytes_to_str as tostr
from validator import infnan_to_zero as rmnan
from adapter import rf2_connector
from process.pitstop import EstimatePitTime

def safe_int(v):
    if isinstance(v, bytes):
        return int.from_bytes(v, "little")
    return int(v)

class DataAdapter:
    __slots__ = ("shmm", "rest")
    def __init__(self, shmm: rf2_connector.RF2Info, rest=None) -> None:
        self.shmm = shmm
        self.rest = rest

class TelemetryData(DataAdapter):
    __slots__ = ()

    def id(self, index: int | None = None) -> int: return self.shmm.rf2TeleVeh(index).mID
    def time_elapsed(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mElapsedTime)
    def lap_number(self, index: int | None = None) -> int: return self.shmm.rf2TeleVeh(index).mLapNumber
    def lap_distance(self, index: int | None = None) -> float:
        try:
            return rmnan(self.shmm.rf2ScorVeh(index).mLapDist)
        except Exception:
            return 0.0
    def gear(self, index: int | None = None) -> int: return self.shmm.rf2TeleVeh(index).mGear

    def rpm(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mEngineRPM)
    def rpm_max(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mEngineMaxRPM)
    def temp_oil(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mEngineOilTemp)
    def temp_water(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mEngineWaterTemp)
    def turbo_pressure(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mTurboBoostPressure)
    def engine_torque(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mEngineTorque)
    def steering_shaft_torque(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mSteeringShaftTorque)

    def fuel_level(self, index: int | None = None) -> float:
        return rmnan(self.shmm.rf2TeleVeh(index).mFuel)

    def fuel_capacity(self, index: int | None = None) -> float:
        return rmnan(self.shmm.rf2TeleVeh(index).mFuelCapacity)

    def fuel_percent(self, index: int | None = None) -> float:
        scor_veh = self.shmm.rf2ScorVeh(index)
        return rmnan(scor_veh.mFuelFraction) / 255.0

    def input_throttle(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mFilteredThrottle)
    def input_brake(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mFilteredBrake)
    def input_clutch(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mFilteredClutch)
    def input_steering(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mFilteredSteering)

    def unfiltered_throttle(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mUnfilteredThrottle)
    def unfiltered_brake(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mUnfilteredBrake)
    def unfiltered_clutch(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mUnfilteredClutch)

    def wing_front(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mFrontWingHeight)
    def drag(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mDrag)
    def downforce_front(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mFrontDownforce)
    def downforce_rear(self, index: int | None = None) -> float: return rmnan(self.shmm.rf2TeleVeh(index).mRearDownforce)

    def car_state(self, index: int | None = None) -> dict:
        veh = self.shmm.rf2TeleVeh(index)
        scor_veh = self.shmm.rf2ScorVeh(index)
        return {
            "speed_limiter": bool(veh.mSpeedLimiter),
            "headlights": bool(veh.mHeadlights),
            "ignition": safe_int(veh.mIgnitionStarter),
            "brake_bias": rmnan(veh.mRearBrakeBias),
            "drs": bool(scor_veh.mDRSState),
            "attack_mode": safe_int(scor_veh.mAttackMode)
        }

    def electric_data(self, index: int | None = None) -> dict:
        veh = self.shmm.rf2TeleVeh(index)
        return {
            "charge": rmnan(veh.mBatteryChargeFraction),
            "torque": rmnan(veh.mElectricBoostMotorTorque),
            "rpm": rmnan(veh.mElectricBoostMotorRPM),
            "temp_motor": rmnan(veh.mElectricBoostMotorTemperature),
            "temp_water": rmnan(veh.mElectricBoostWaterTemperature),
            "state": safe_int(veh.mElectricBoostMotorState)
        }

    def lmu_electronics(self, index: int | None = None) -> dict:
        veh = self.shmm.rf2TeleVeh(index)
        if not veh: return {}
        return {
            "tc": safe_int(veh.mTC),
            "tc_max": safe_int(veh.mTCMax),
            "tc_slip": safe_int(veh.mTCSlip),
            "tc_slip_max": safe_int(veh.mTCSlipMax),
            "tc_cut": safe_int(veh.mTCCut),
            "tc_cut_max": safe_int(veh.mTCCutMax),
            "abs": safe_int(veh.mABS),
            "abs_max": safe_int(veh.mABSMax),
            "brake_migration": safe_int(veh.mMigration),
            "brake_migration_max": safe_int(veh.mMigrationMax),
            "motor_map": safe_int(veh.mMotorMap),
            "motor_map_max": safe_int(veh.mMotorMapMax),
            "anti_sway_front": safe_int(veh.mFrontAntiSway),
            "anti_sway_front_max": safe_int(veh.mFrontAntiSwayMax),
            "anti_sway_rear": safe_int(veh.mRearAntiSway),
            "anti_sway_rear_max": safe_int(veh.mRearAntiSwayMax),
            "tc_active": bool(veh.mTCActive),
            "abs_active": bool(veh.mABSActive),
            "speed_limiter_active": bool(veh.mSpeedLimiterActive),
            "wiper_state": safe_int(veh.mWiperState)
        }

    def lmu_extra_telemetry(self, index: int | None = None) -> dict:
        veh = self.shmm.rf2TeleVeh(index)
        if not veh: return {}
        return {
            "lap_invalidated": bool(veh.mLapInvalidated),
            "lift_and_coast_progress": safe_int(veh.mLiftAndCoastProgress),
            "track_limits_steps": safe_int(veh.mTrackLimitsSteps),
            "regen_kw": rmnan(veh.mRegen),
            "state_of_charge": rmnan(veh.mStateOfCharge),
            "virtual_energy": rmnan(veh.mVirtualEnergy),
            "gap_car_ahead": rmnan(veh.mTimeGapCarAhead),
            "gap_car_behind": rmnan(veh.mTimeGapCarBehind),
            "gap_place_ahead": rmnan(veh.mTimeGapPlaceAhead),
            "gap_place_behind": rmnan(veh.mTimeGapPlaceBehind),
            "vehicle_model": tostr(veh.mVehicleModel),
            "vehicle_class_id": safe_int(veh.mVehicleClass),
            "vehicle_championship": safe_int(veh.mVehicleChampionship)
        }

    def lmu_extra_telemetry(self, index: int | None = None) -> dict:
        veh = self.shmm.rf2TeleVeh(index)
        if not veh: return {}
        return {
            "lap_invalidated": bool(veh.mLapInvalidated),
            "lift_and_coast_progress": safe_int(veh.mLiftAndCoastProgress),
            "track_limits_steps": safe_int(veh.mTrackLimitsSteps),
            "regen_kw": rmnan(veh.mRegen),
            "state_of_charge": rmnan(veh.mStateOfCharge),
            "virtual_energy": rmnan(veh.mVirtualEnergy),
            "gap_car_ahead": rmnan(veh.mTimeGapCarAhead),
            "gap_car_behind": rmnan(veh.mTimeGapCarBehind),
            "gap_place_ahead": rmnan(veh.mTimeGapPlaceAhead),
            "gap_place_behind": rmnan(veh.mTimeGapPlaceBehind),
            "vehicle_model": tostr(veh.mVehicleModel),
            "vehicle_class_id": safe_int(veh.mVehicleClass),
            "vehicle_championship": safe_int(veh.mVehicleChampionship)
        }

    def lmu_wheels_extra(self, index: int | None = None) -> dict:
        wheels = self.shmm.rf2TeleVeh(index).mWheels
        data = {}
        pos_map = {0: "fl", 1: "fr", 2: "rl", 3: "rr"}
        for i, pos in pos_map.items():
            w = wheels[i]
            data[pos] = {
                "toe": rmnan(w.mToe),
                "optimal_temp": rmnan(w.mOptimalTemp),
                "compound_index": safe_int(w.mCompoundIndex),
                "compound_type": safe_int(w.mCompoundType)
            }
        return data

    def virtual_energy(self, index: int | None = None) -> float:
        # LMU inclut nativement la fraction de Virtual Energy
        veh = self.shmm.rf2TeleVeh(index)
        ve_frac = rmnan(veh.mVirtualEnergy)
        return ve_frac * 100.0

    def max_virtual_energy(self, index: int | None = None) -> float: return 100.0

    def suspension_deflection(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mSuspensionDeflection) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def ride_height(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mRideHeight) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def suspension_force(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mSuspForce) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def brake_pressure_list(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mBrakePressure) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def lateral_force(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mLateralForce) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def longitudinal_force(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mLongitudinalForce) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def tire_load(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mTireLoad) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def tire_carcass_temp(self, index: int | None = None) -> list[float]:
        return [rmnan(w.mTireCarcassTemperature) - 273.15 for w in self.shmm.rf2TeleVeh(index).mWheels]

    def tire_inner_layer_temp(self, index: int | None = None) -> list[float]:
        wheels = self.shmm.rf2TeleVeh(index).mWheels
        res = []
        for w in wheels:
            temps = [rmnan(t) for t in w.mTireInnerLayerTemperature]
            avg = sum(temps) / 3.0 if temps else 0.0
            res.append(avg - 273.15)
        return res

    def wheel_details(self, index: int | None = None) -> dict:
        wheels = self.shmm.rf2TeleVeh(index).mWheels
        data = {}
        pos_map = {0: "fl", 1: "fr", 2: "rl", 3: "rr"}
        for i, pos in pos_map.items():
            w = wheels[i]
            data[pos] = {
                "brake_pressure": rmnan(w.mBrakePressure),
                "camber": rmnan(w.mCamber),
                "load": rmnan(w.mTireLoad),
                "grip_fract": rmnan(w.mGripFract),
                "temp_carcass": rmnan(w.mTireCarcassTemperature) - 273.15,
                "ride_height": rmnan(w.mRideHeight)
            }
        return data

    def tire_temp_details(self, index: int | None = None) -> dict:
        wheels = self.shmm.rf2TeleVeh(index).mWheels
        data = {}
        pos_map = {0: "fl", 1: "fr", 2: "rl", 3: "rr"}
        for i, pos in pos_map.items():
            w = wheels[i]
            data[pos] = {
                "surface": [rmnan(t) - 273.15 for t in w.mTemperature],
                "inner":   [rmnan(t) - 273.15 for t in w.mTireInnerLayerTemperature],
                "carcass": rmnan(w.mTireCarcassTemperature) - 273.15
            }
        return data

    def tire_temps(self, index: int | None = None) -> dict:
        wheels = self.shmm.rf2TeleVeh(index).mWheels
        return {
            "fl": [rmnan(t) - 273.15 for t in wheels[0].mTemperature],
            "fr": [rmnan(t) - 273.15 for t in wheels[1].mTemperature],
            "rl": [rmnan(t) - 273.15 for t in wheels[2].mTemperature],
            "rr": [rmnan(t) - 273.15 for t in wheels[3].mTemperature]
        }

    def local_velocity(self, index: int | None = None) -> tuple[float, float, float]:
        vel = self.shmm.rf2TeleVeh(index).mLocalVel
        return rmnan(vel.x), rmnan(vel.y), rmnan(vel.z)

    def local_acceleration(self, index: int | None = None) -> tuple[float, float, float]:
        accel = self.shmm.rf2TeleVeh(index).mLocalAccel
        return rmnan(accel.x), rmnan(accel.y), rmnan(accel.z)

    def local_rot_acceleration(self, index: int | None = None) -> tuple[float, float, float]:
        rot_accel = self.shmm.rf2TeleVeh(index).mLocalRotAccel
        return rmnan(rot_accel.x), rmnan(rot_accel.y), rmnan(rot_accel.z)

    def tire_pressure(self, index: int | None = None) -> list[float]: return [rmnan(w.mPressure) for w in self.shmm.rf2TeleVeh(index).mWheels]
    def tire_wear(self, index: int | None = None) -> list[float]: return [rmnan(w.mWear) for w in self.shmm.rf2TeleVeh(index).mWheels]

    def tire_compound_name(self, index: int | None = None) -> dict:
        try:
            veh = self.shmm.rf2TeleVeh(index)
            front = tostr(veh.mFrontTireCompoundName)
            rear = tostr(veh.mRearTireCompoundName)
            return {"fl": front, "fr": front, "rl": rear, "rr": rear}
        except:
            return {"fl": "---", "fr": "---", "rl": "---", "rr": "---"}

    def brake_temp(self, index: int | None = None) -> list[float]: return [rmnan(w.mBrakeTemp) - 273.15 for w in self.shmm.rf2TeleVeh(index).mWheels]

    def brake_wear(self, index: int | None = None) -> tuple[float, float, float, float]:
        if self.rest: return getattr(self.rest.telemetry, 'brakeWear', (0.0, 0.0, 0.0, 0.0))
        return (0.0, 0.0, 0.0, 0.0)

    def surface_type(self, index: int | None = None) -> list[int]: return [safe_int(w.mSurfaceType) for w in self.shmm.rf2TeleVeh(index).mWheels]
    def wheel_detached(self, index: int | None = None) -> list[bool]: return [bool(w.mDetached) for w in self.shmm.rf2TeleVeh(index).mWheels]
    def tire_flat(self, index: int | None = None) -> list[bool]: return [bool(w.mFlat) for w in self.shmm.rf2TeleVeh(index).mWheels]
    def dents(self, index: int | None = None) -> list[int]: return [safe_int(x) for x in self.shmm.rf2TeleVeh(index).mDentSeverity]
    def overheating(self, index: int | None = None) -> bool: return bool(self.shmm.rf2TeleVeh(index).mOverheating)


class ScoringData(DataAdapter):
    __slots__ = ()
    def flag_state(self) -> dict:
        info = self.shmm.rf2ScorInfo
        return {
            "yellow_global": safe_int(info.mYellowFlagState),
            "sector_flags": [safe_int(x) for x in info.mSectorFlag],
            "in_realtime": safe_int(info.mInRealtime),
            "start_light": safe_int(info.mStartLight),
            "red_lights_num": safe_int(info.mNumRedLights)
        }
    def track_name(self) -> str: return tostr(self.shmm.rf2ScorInfo.mTrackName)
    def track_length(self) -> float: return rmnan(self.shmm.rf2ScorInfo.mLapDist)
    def session_type(self) -> int: return safe_int(self.shmm.rf2ScorInfo.mSession)
    def time_info(self) -> dict:
        info = self.shmm.rf2ScorInfo
        return {"current": rmnan(info.mCurrentET), "end": rmnan(info.mEndET), "max_laps": info.mMaxLaps}
    def game_phase(self) -> int: return safe_int(self.shmm.rf2ScorInfo.mGamePhase)
    def weather_env(self) -> dict:
        info = self.shmm.rf2ScorInfo
        return {
            "ambient_temp": rmnan(info.mAmbientTemp),
            "track_temp": rmnan(info.mTrackTemp),
            "rain": rmnan(info.mRaining),
            "darkness": rmnan(info.mDarkCloud),
            "wetness_path": (rmnan(info.mMinPathWetness), rmnan(info.mMaxPathWetness)),
            "wind_speed": rmnan((info.mWind.x**2 + info.mWind.y**2 + info.mWind.z**2)**0.5)
        }
    def vehicle_count(self) -> int: return self.shmm.rf2ScorInfo.mNumVehicles
    def get_vehicle_scoring(self, index: int) -> dict:
        veh = self.shmm.rf2ScorVeh(index)
        if not veh: return {}
        sector_map = {0: 3, 1: 1, 2: 2}
        return {
            "id": veh.mID,
            "driver": tostr(veh.mDriverName),
            "vehicle": tostr(veh.mVehicleName),
            "class": tostr(veh.mVehicleClass),
            "position": safe_int(veh.mPlace),
            "is_player": safe_int(veh.mIsPlayer),
            "laps": veh.mTotalLaps,
            "sector": sector_map.get(safe_int(veh.mSector), 0),
            "status": safe_int(veh.mFinishStatus),
            "pit_state": safe_int(veh.mPitState),
            "in_pits": safe_int(veh.mInPits),
            "pit_group": tostr(veh.mPitGroup),
            "pit_stops": safe_int(veh.mNumPitstops),
            "penalties": safe_int(veh.mNumPenalties),
            "lap_dist": rmnan(veh.mLapDist),
            "best_lap": rmnan(veh.mBestLapTime),
            "last_lap": rmnan(veh.mLastLapTime),
            "sectors_best": (rmnan(veh.mBestSector1), rmnan(veh.mBestSector2)),
            "sectors_cur": (rmnan(veh.mCurSector1), rmnan(veh.mCurSector2)),
            "gap_leader": rmnan(veh.mTimeBehindLeader),
            "gap_next": rmnan(veh.mTimeBehindNext),
            "flag": safe_int(veh.mFlag),
            "under_yellow": bool(veh.mUnderYellow),
            "x": rmnan(veh.mPos.x),
            "z": rmnan(veh.mPos.z),
        }

    def lmu_scoring_extra(self) -> dict:
        info = self.shmm.rf2ScorInfo
        if not info: return {}
        return {
            "session_time_remaining": rmnan(info.mSessionTimeRemaining),
            "time_of_day": rmnan(info.mTimeOfDay),
            "is_fixed_setup": bool(info.mIsFixedSetup),
            "track_grip_level": safe_int(info.mTrackGripLevel),
            "cloud_coverage": safe_int(info.mCloudCoverage),
            "track_limits_steps_per_penalty": safe_int(info.mTrackLimitsStepsPerPenalty),
            "track_limits_steps_per_point": safe_int(info.mTrackLimitsStepsPerPoint)
        }

class RulesData(DataAdapter):
    __slots__ = ()
    def sc_info(self) -> dict: return {"active": 0, "laps": 0, "instruction": 0}
    def yellow_flag(self) -> dict: return {"detected": 0, "state": 0, "laps": 0}
    def message(self) -> str: return ""
    def participant_status(self, index: int) -> dict: return {}

class ExtendedData(DataAdapter):
    __slots__ = ()
    def physics_options(self) -> dict: return {"tc": 0, "abs": 0, "fuel_mult": 1.0, "tire_mult": 1.0}
    def pit_limit(self) -> float: return 16.6 # 60km/h fallback LMU

class PitInfoData(DataAdapter):
    __slots__ = ()
    def menu_status(self) -> dict:
        return {"cat_idx": 0, "cat_name": "", "choice_idx": 0, "choice_str": "", "num_choices": 0}

class WeatherData(DataAdapter):
    __slots__ = ()
    def info(self) -> dict:
        sinfo = self.shmm.rf2ScorInfo
        ambient_c = rmnan(sinfo.mAmbientTemp)
        rain_val = rmnan(sinfo.mRaining)
        clouds = rmnan(sinfo.mDarkCloud)
        return {"et": rmnan(sinfo.mCurrentET), "cloudiness": clouds, "ambient_temp": ambient_c, "rain_intensity": rain_val}

    def forecast(self) -> dict:
        if not self.rest: return {}
        def _format_nodes(nodes):
            return [{"start_percent": n.start_percent, "sky": n.sky_type, "temp": n.temperature, "rain_chance": n.rain_chance} for n in nodes]
        return {
            "practice": _format_nodes(getattr(self.rest.telemetry, 'forecastPractice', [])),
            "qualify": _format_nodes(getattr(self.rest.telemetry, 'forecastQualify', [])),
            "race": _format_nodes(getattr(self.rest.telemetry, 'forecastRace', []))
        }

class PitStrategyData:
    __slots__ = ("_pit_estimator", "_port", "_cache", "_cache_time")
    _CACHE_TTL = 2.0

    def __init__(self, port=5397):
        self._pit_estimator = EstimatePitTime()
        self._port = port
        self._cache: dict = {}
        self._cache_time: float = 0.0

    def pit_estimate(self) -> dict:
        now = time.monotonic()
        if now - self._cache_time < self._CACHE_TTL:
            return self._cache
        try:
            url = f"http://localhost:{self._port}/rest/garage/UIScreen/RepairAndRefuel"
            resp = requests.get(url, timeout=0.1)
            if resp.status_code == 200:
                est = self._pit_estimator(resp.json())
                self._cache = {"time_min": est[0], "time_max": est[1],
                               "fuel_to_add": est[2], "laps_to_add": est[3]}
                self._cache_time = now
                return self._cache
        except:
            pass
        self._cache_time = now
        return self._cache

class Vehicle(DataAdapter):
    __slots__ = ()
    def speed(self, index: int | None = None) -> float:
        veh = self.shmm.rf2TeleVeh(index)
        if not veh: return 0.0
        vel = veh.mLocalVel
        speed_ms = (vel.x**2 + vel.y**2 + vel.z**2)**0.5
        return speed_ms * 3.6

    def aero_damage(self, index: int | None = None) -> float: return 0.0

    def get_local_driver_status(self) -> dict:
        from adapter.rf2_connector import INVALID_INDEX
        idx = self.shmm.playerIndex
        if idx == INVALID_INDEX:
            return {
                "is_driving": False,
                "driver_name": "Unknown",
                "vehicle_index": -1,
                "is_player": False,
                "control": -1,
                "in_realtime": False
            }

        scor_veh = self.shmm.rf2ScorVeh(idx)
        in_realtime = (safe_int(self.shmm.rf2ScorInfo.mInRealtime) == 1
                       or safe_int(self.shmm.rf2TeleVeh(idx).mIgnitionStarter) > 0)
        is_player = (safe_int(scor_veh.mIsPlayer) == 1)
        control = safe_int(scor_veh.mControl)
        is_driving = (is_player
                      and control == 0
                      and in_realtime)
        return {
            "is_driving": is_driving,
            "driver_name": tostr(scor_veh.mDriverName),
            "vehicle_index": idx,
            "is_player": is_player,
            "control": control,
            "in_realtime": in_realtime
        }
