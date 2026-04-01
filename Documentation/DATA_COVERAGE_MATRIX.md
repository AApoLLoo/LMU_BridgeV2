# Data Coverage Matrix (REST + SharedMemory)

## Objectif
Comparer les donnees disponibles dans `SharedMemory` / `REST API` et les donnees effectivement consommees dans `bridge.py`.

## Resume rapide
- SharedMemory via `TelemetryData`: couverture elevee, mais pas complete.
- REST API via `RestAPIData`: couverture partielle (meteo + frein + nouveau bloc `restapi`).
- Certains champs restent non exploites volontairement ou non prioritaires.

## SharedMemory - TelemetryData

| Source brute | Methode adapter | Utilisee dans payload | Statut |
|---|---|---|---|
| `mLapDist` (scoring veh) | `lap_distance()` | Oui (`TelemetryRecorder`) | OK |
| `mEngineTorque` | `engine_torque()` | Oui (`telemetry.engine_torque`) | OK |
| `mSteeringShaftTorque` | `steering_shaft_torque()` | Oui (`telemetry.steering_shaft_torque`) | OK |
| `mLocalAccel` | `local_acceleration()` | Oui (`telemetry.local_acceleration`) | OK |
| `mLocalRotAccel` | `local_rot_acceleration()` | Oui (`telemetry.local_rot_acceleration`) | OK |
| `mFuelFraction` | `fuel_percent()` | Non | Non utilise |
| `mFrontWingHeight` | `wing_front()` | Non | Non utilise |
| detail roues derive | `wheel_details()` | Non | Non utilise |
| details temperatures pneus | `tire_temp_details()` | Non | Non utilise |
| temps ecoule session | `time_elapsed()` | Non | Non utilise |

## REST API - RestAPIData

| Champ RestAPIData | Expose dans payload | Statut |
|---|---|---|
| `forecastPractice/forecastQualify/forecastRace` | Oui (`weatherForecast`) | OK |
| `brakeWear` | Oui (`telemetry.tires.brake_wear`) | OK |
| `timeScale` | Oui (`restapi.time_scale`) | OK |
| `trackClockTime` | Oui (`restapi.track_clock_time`) | OK |
| `privateQualifying` | Oui (`restapi.private_qualifying`) | OK |
| `steeringWheelRange` | Oui (`restapi.steering_wheel_range`) | OK |
| `currentVirtualEnergy` | Oui (`restapi.current_virtual_energy`) | OK |
| `maxVirtualEnergy` | Oui (`restapi.max_virtual_energy`) | OK |
| `expectedFuelConsumption` | Oui (`restapi.expected_fuel_consumption`) | OK |
| `expectedVirtualEnergyConsumption` | Oui (`restapi.expected_virtual_energy_consumption`) | OK |
| `aeroDamage` | Oui (`restapi.aero_damage`) | OK |
| `penaltyTime` | Oui (`restapi.penalty_time`) | OK |
| `suspensionDamage` | Oui (`restapi.suspension_damage`) | OK |
| `stintUsage` | Oui (`restapi.stint_usage`) | OK |
| `pitStopEstimate` | Oui (`restapi.pit_stop_estimate`) | OK |

## Ecarts restants (priorite fonctionnelle)

1. **Non exploites TelemetryData**: `fuel_percent`, `wing_front`, `wheel_details`, `tire_temp_details`, `time_elapsed`.
2. **Champs SDK non mappes** (directement dans `InternalsPlugin.hpp`): ex. `mEngineClutchRPM`, `mDeltaBest`, certains champs scoring avance, etc.
3. **Duplication a nettoyer** dans `adapter/rf2_data.py`: `lmu_extra_telemetry` est defini 2 fois (comportement identique, mais dette technique).

## Recommandation
- Etape 1: garder l'actuel (stable) et monitorer perf/taille payload.
- Etape 2: activer au besoin `fuel_percent` + `time_elapsed` (faible cout, utile UI).
- Etape 3: ajouter un mode "payload detaille" optionnel pour `wheel_details` et `tire_temp_details` afin d'eviter d'alourdir le flux par defaut.

