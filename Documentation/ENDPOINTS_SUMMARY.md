# ENDPOINTS SUMMARY

Ce document liste les endpoints reperes dans le code du projet `LMU_BridgeV2`.
Il est base sur les appels reels presents dans les fichiers Python (pas sur des suppositions serveur).

## 1) API locale LMU/rF2 (`http://localhost:<port>`)

### Endpoints REST consommes par `RestAPIInfo` (tasksets)
Source: `adapter/rf2_restapi.py`

#### Taskset LMU
- `GET /rest/sessions/weather`
- `GET /rest/sessions`
- `GET /rest/garage/getPlayerGarageData`
- `GET /rest/garage/UIScreen/RepairAndRefuel`
- `GET /rest/strategy/pitstop-estimate`
- `GET /rest/strategy/usage`

#### Taskset RF2
- `GET /rest/sessions/weather`
- `GET /rest/sessions/setting/SESSSET_race_timescale`
- `GET /rest/sessions/setting/SESSSET_private_qual`
- `GET /rest/garage/fuel`

### Endpoints locaux utilitaires appeles ailleurs
- `GET /rest/garage/UIScreen/RepairAndRefuel`
  - Source: `adapter/rf2_data.py` (`PitStrategyData.pit_estimate`)

## 2) Endpoints monitor/script (outil de debug)

Source: `lmu_telemetry_listener.py` (script de monitoring)

- `GET /rest/watch/sessionInfo`
- `GET /rest/sessions/weather`
- `GET /rest/strategy/usage`
- `GET /rest/strategy/pitstop-estimate`
- `GET /rest/watch/standings`
- `GET /rest/garage/tireinfo`
- `GET /rest/race/car`

## 3) Endpoints VPS / backend distant (`https://api.racetelemetrybyfbt.com`)

### HTTP
- `POST /api/auth/login`
  - Source: `adapter/socket_connector.py`
- `POST /api/telemetry/lap`
  - Source: `bridge.py` (`TelemetryRecorder.flush_lap`)
- `POST /api/sessions/start`
  - Source: `bridge.py` (`BridgeLogic._run`)

### Socket.IO (events)
Source: `adapter/socket_connector.py`

- Emit: `telemetry_data`
- Emit: `presence_update`

## 4) Endpoints setups ajoutes dans le code

Source: `bridge.py` (`SetupManager`)

- `GET /rest/garage/setups`
- `POST /rest/garage/setups/apply`

Note: ces endpoints sont definis dans la classe `SetupManager`. Leur disponibilite depend de l'API jeu exposee localement.

## 5) Ports observes dans le projet

- `6397`: port LMU principal (REST local)
- `5397`: fallback utilise dans certains appels strategy/pit

## 6) Limites de ce resume

- Les methodes HTTP indiquees proviennent des appels explicites (`requests.get` / `requests.post`) dans le code.
- Le document ne garantit pas que tous ces endpoints existent cote serveur dans toutes les versions du jeu.
- Les endpoints list es sont ceux visibles statiquement au moment de la mise a jour.

## 7) Payloads envoyes actuellement

Source principale: `bridge.py` (`BridgeLogic._run`, `TelemetryRecorder.flush_lap`) et `adapter/socket_connector.py`.

### 7.1 `POST /api/auth/login`

```json
{
  "username": "string",
  "password": "string"
}
```

### 7.2 `POST /api/sessions/start`

```json
{
  "sessionId": "string",
  "driver": "string",
  "circuit": "string"
}
```

### 7.3 `POST /api/telemetry/lap`

```json
{
  "sessionId": "string",
  "lapNumber": 0,
  "driver": "string",
  "lapTime": 0.0,
  "invalidated": false,
  "avgSpeed": 0.0,
  "samplesCount": 0,
  "weather": {},
  "samples": [
    {
      "d": 0.0,
      "s": 0.0,
      "x": 0.0,
      "z": 0.0,
      "t": 0,
      "b": 0,
      "g": 0,
      "ut": 0,
      "ub": 0,
      "uc": 0,
      "w": 0.0,
      "f": 0.0,
      "r": 0,
      "ve": 0.0,
      "tw": 0.0,
      "drag": 0.0,
      "df_f": 0.0,
      "df_r": 0.0,
      "susp_def": [0.0, 0.0, 0.0, 0.0],
      "rh": [0.0, 0.0, 0.0, 0.0],
      "susp_f": [0, 0, 0, 0],
      "brk_tmp": [0.0, 0.0, 0.0, 0.0],
      "brk_prs": [0.0, 0.0, 0.0, 0.0],
      "lat_f": [0, 0, 0, 0],
      "long_f": [0, 0, 0, 0],
      "t_load": [0, 0, 0, 0],
      "t_temp_c": [0.0, 0.0, 0.0, 0.0],
      "t_temp_i": [0.0, 0.0, 0.0, 0.0]
    }
  ]
}
```

### 7.4 Event Socket.IO `telemetry_data` (payload live)

```json
{
  "teamId": "string",
  "driverName": "string",
  "activeDriverId": "string",
  "lastLapFuelConsumption": 0.0,
  "averageConsumptionFuel": 0.0,
  "lastLapVEConsumption": 0.0,
  "averageConsumptionVE": 0.0,
  "sessionTimeRemainingSeconds": 0.0,
  "weatherForecast": [
    { "rain": 0.0, "cloud": 0.0, "temp": 0.0 }
  ],
  "telemetry": {
    "gear": 0,
    "rpm": 0.0,
    "speed": 0.0,
    "maxRpm": 0.0,
    "fuel": 0.0,
    "fuelCapacity": 0.0,
    "inputs": { "thr": 0.0, "brk": 0.0, "clt": 0.0, "str": 0.0 },
    "brake_bias": 0.0,
    "car_state": {
      "speed_limiter": false,
      "headlights": false,
      "ignition": 0,
      "drs": false,
      "attack_mode": 0
    },
    "turbo_pressure": 0.0,
    "local_velocity": { "x": 0.0, "y": 0.0, "z": 0.0 },
    "vehicle_health": {
      "overheating": false,
      "tire_flat_count": 0,
      "wheel_detached_count": 0,
      "dents_max": 0,
      "by_wheel": {
        "fl": { "flat": false, "detached": false },
        "fr": { "flat": false, "detached": false },
        "rl": { "flat": false, "detached": false },
        "rr": { "flat": false, "detached": false }
      }
    },
    "temps": { "oil": 0.0, "water": 0.0 },
    "tires": {
      "temp": {},
      "press": [0.0, 0.0, 0.0, 0.0],
      "wear": [0.0, 0.0, 0.0, 0.0],
      "brake_wear": [0.0, 0.0, 0.0, 0.0],
      "type": [0, 0, 0, 0],
      "brake_temp": [0.0, 0.0, 0.0, 0.0],
      "compounds": { "fl": "---", "fr": "---", "rl": "---", "rr": "---" }
    },
    "electric": {
      "charge": 0.0,
      "torque": 0.0,
      "rpm": 0.0,
      "temp_motor": 0.0,
      "temp_water": 0.0,
      "state": 0
    },
    "virtual_energy": 0.0,
    "max_virtual_energy": 100.0,
    "lmu_electronics": {},
    "lmu_extra": {},
    "lmu_wheels_extra": {},
    "leaderLaps": 0,
    "leaderAvgLapTime": 0.0,
    "position": 0,
    "lastLap": 0
  },
  "scoring": {
    "track": "string",
    "time": { "current": 0.0, "end": 0.0, "max_laps": 0, "session": "string" },
    "flags": {},
    "weather": {},
    "vehicles": [],
    "vehicle_data": {},
    "length": 0.0,
    "lmu_scoring_extra": {}
  },
  "rules": { "sc": {}, "yellow": {}, "my_status": {} },
  "pit": { "menu": {}, "strategy": {} },
  "weather_det": {},
  "extended": { "physics": {}, "pit_limit": 0.0 }
}
```

### 7.5 Event Socket.IO `presence_update`

Le payload est libre et depend de l'appelant de `send_presence(data)`.

