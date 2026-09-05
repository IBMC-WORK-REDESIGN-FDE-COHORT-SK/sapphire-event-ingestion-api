#!/usr/bin/env python3
"""
Generate realistic sample health metrics data for testing
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import random

# User configurations
USERS = [
    {
        "user_id": "michael.davis@sapphirewellness.com",
        "device_id": "apple-watch-md-001",
        "device_type": "smartwatch",
        "device_manufacturer": "Apple",
        "device_model": "Apple Watch Series 9",
        "profile": "active_male"  # More active, higher metrics
    },
    {
        "user_id": "sarah.johnson@sapphirewellness.com",
        "device_id": "fitbit-sj-002",
        "device_type": "fitness_band",
        "device_manufacturer": "Fitbit",
        "device_model": "Fitbit Charge 6",
        "profile": "moderate_female"  # Moderate activity
    }
]

# Base timestamp (yesterday at midnight UTC)
BASE_TIME = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

def get_timestamp_nano(hours=0, minutes=0):
    """Get Unix timestamp in nanoseconds"""
    dt = BASE_TIME + timedelta(hours=hours, minutes=minutes)
    return int(dt.timestamp() * 1e9)

def generate_activity_data(user, hour_start, hour_end):
    """Generate activity metrics (steps, distance, calories) for a time range"""
    data_points = []
    
    # Profile-based multipliers
    multipliers = {
        "active_male": {"steps": 1.3, "distance": 1.2, "calories": 1.25},
        "moderate_female": {"steps": 1.0, "distance": 1.0, "calories": 1.0}
    }
    mult = multipliers[user["profile"]]
    
    # Generate data every 30 minutes
    for hour in range(hour_start, hour_end):
        for minute in [0, 30]:
            # Vary activity based on time of day
            if 7 <= hour < 9:  # Morning routine
                base_steps = random.randint(800, 1200)
            elif 12 <= hour < 13:  # Lunch walk
                base_steps = random.randint(600, 900)
            elif 17 <= hour < 19:  # Evening exercise
                base_steps = random.randint(1000, 1500)
            elif 22 <= hour or hour < 6:  # Sleep
                base_steps = random.randint(0, 50)
            else:  # Regular activity
                base_steps = random.randint(300, 600)
            
            steps = int(base_steps * mult["steps"])
            distance = round(steps * 0.75 * mult["distance"], 1)  # ~0.75m per step
            calories = round(steps * 0.04 * mult["calories"], 1)  # ~0.04 kcal per step
            
            start_time = get_timestamp_nano(hour, minute)
            end_time = get_timestamp_nano(hour, minute + 30)
            
            data_points.append({
                "steps": steps,
                "distance": distance,
                "calories": calories,
                "start_time": start_time,
                "end_time": end_time
            })
    
    return data_points

def create_activity_payload(user, data_points):
    """Create activity metrics payload"""
    metrics = []
    
    for dp in data_points:
        # Steps metric
        metrics.append({
            "name": "health.activity.steps",
            "description": "Step count in 30-minute window",
            "unit": "steps",
            "data": {
                "data_points": [{
                    "attributes": {"aggregation_window": "30m"},
                    "start_time_unix_nano": dp["start_time"],
                    "time_unix_nano": dp["end_time"],
                    "value": dp["steps"]
                }]
            }
        })
        
        # Distance metric
        metrics.append({
            "name": "health.activity.distance",
            "description": "Distance traveled",
            "unit": "m",
            "data": {
                "data_points": [{
                    "attributes": {"aggregation_window": "30m"},
                    "start_time_unix_nano": dp["start_time"],
                    "time_unix_nano": dp["end_time"],
                    "value": dp["distance"]
                }]
            }
        })
        
        # Calories metric
        metrics.append({
            "name": "health.activity.calories",
            "description": "Calories burned",
            "unit": "kcal",
            "data": {
                "data_points": [{
                    "attributes": {"aggregation_window": "30m"},
                    "start_time_unix_nano": dp["start_time"],
                    "time_unix_nano": dp["end_time"],
                    "value": dp["calories"]
                }]
            }
        })
    
    return {
        "request_id": f"req-activity-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": metrics[:30]  # Limit to 30 metrics per request
    }

def create_heartrate_payload(user):
    """Create heart rate metrics for the day"""
    data_points = []
    
    # Profile-based heart rate ranges
    hr_ranges = {
        "active_male": {"resting": (58, 65), "active": (120, 160), "max": 185},
        "moderate_female": {"resting": (62, 70), "active": (110, 145), "max": 175}
    }
    hr = hr_ranges[user["profile"]]
    
    # Generate continuous heart rate every 5 minutes during waking hours
    for hour in range(6, 23):  # 6 AM to 11 PM
        for minute in range(0, 60, 5):
            # Determine heart rate based on activity
            if 7 <= hour < 8 or 18 <= hour < 19:  # Exercise time
                bpm = random.randint(hr["active"][0], hr["active"][1])
            elif 22 <= hour:  # Winding down
                bpm = random.randint(hr["resting"][0], hr["resting"][1] + 10)
            else:  # Normal activity
                bpm = random.randint(hr["resting"][1], hr["active"][0])
            
            data_points.append({
                "attributes": {"measurement_type": "continuous"},
                "start_time_unix_nano": None,
                "time_unix_nano": get_timestamp_nano(hour, minute),
                "value": float(bpm)
            })
    
    # Add resting heart rate (morning measurement)
    resting_bpm = random.randint(hr["resting"][0], hr["resting"][1])
    
    # Add max heart rate (during exercise)
    max_bpm = random.randint(hr["max"] - 10, hr["max"])
    
    return {
        "request_id": f"req-heartrate-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": [
            {
                "name": "health.heartrate.bpm",
                "description": "Continuous heart rate monitoring",
                "unit": "beats/min",
                "data": {"data_points": data_points[:50]}  # Limit data points
            },
            {
                "name": "health.heartrate.resting",
                "description": "Resting heart rate",
                "unit": "beats/min",
                "data": {
                    "data_points": [{
                        "attributes": {"measurement_time": "morning"},
                        "start_time_unix_nano": None,
                        "time_unix_nano": get_timestamp_nano(7, 0),
                        "value": float(resting_bpm)
                    }]
                }
            },
            {
                "name": "health.heartrate.max",
                "description": "Maximum heart rate",
                "unit": "beats/min",
                "data": {
                    "data_points": [{
                        "attributes": {"activity": "running"},
                        "start_time_unix_nano": None,
                        "time_unix_nano": get_timestamp_nano(18, 30),
                        "value": float(max_bpm)
                    }]
                }
            }
        ]
    }

def create_sleep_payload(user):
    """Create sleep metrics"""
    # Sleep from 11 PM to 7 AM (8 hours)
    sleep_start = get_timestamp_nano(23, 0) - (24 * 3600 * 1000000000)  # Previous day
    sleep_end = get_timestamp_nano(7, 0)
    
    # Profile-based sleep quality
    quality_ranges = {
        "active_male": (75, 85),
        "moderate_female": (78, 88)
    }
    quality = random.randint(*quality_ranges[user["profile"]])
    
    # Sleep stages (in seconds)
    total_sleep = 8 * 3600  # 8 hours
    deep_sleep = int(total_sleep * random.uniform(0.15, 0.20))  # 15-20%
    rem_sleep = int(total_sleep * random.uniform(0.20, 0.25))   # 20-25%
    light_sleep = int(total_sleep * random.uniform(0.50, 0.55)) # 50-55%
    awake = total_sleep - (deep_sleep + rem_sleep + light_sleep)
    
    return {
        "request_id": f"req-sleep-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": [
            {
                "name": "health.sleep.duration",
                "description": "Total sleep duration",
                "unit": "s",
                "data": {
                    "data_points": [{
                        "attributes": {},
                        "start_time_unix_nano": sleep_start,
                        "time_unix_nano": sleep_end,
                        "value": float(total_sleep)
                    }]
                }
            },
            {
                "name": "health.sleep.stage.deep",
                "description": "Deep sleep duration",
                "unit": "s",
                "data": {
                    "data_points": [{
                        "attributes": {},
                        "start_time_unix_nano": sleep_start,
                        "time_unix_nano": sleep_end,
                        "value": float(deep_sleep)
                    }]
                }
            },
            {
                "name": "health.sleep.stage.light",
                "description": "Light sleep duration",
                "unit": "s",
                "data": {
                    "data_points": [{
                        "attributes": {},
                        "start_time_unix_nano": sleep_start,
                        "time_unix_nano": sleep_end,
                        "value": float(light_sleep)
                    }]
                }
            },
            {
                "name": "health.sleep.stage.rem",
                "description": "REM sleep duration",
                "unit": "s",
                "data": {
                    "data_points": [{
                        "attributes": {},
                        "start_time_unix_nano": sleep_start,
                        "time_unix_nano": sleep_end,
                        "value": float(rem_sleep)
                    }]
                }
            },
            {
                "name": "health.sleep.stage.awake",
                "description": "Awake time during sleep",
                "unit": "s",
                "data": {
                    "data_points": [{
                        "attributes": {},
                        "start_time_unix_nano": sleep_start,
                        "time_unix_nano": sleep_end,
                        "value": float(awake)
                    }]
                }
            },
            {
                "name": "health.sleep.quality",
                "description": "Sleep quality score",
                "unit": "score",
                "data": {
                    "data_points": [{
                        "attributes": {},
                        "start_time_unix_nano": sleep_start,
                        "time_unix_nano": sleep_end,
                        "value": float(quality)
                    }]
                }
            }
        ]
    }

def create_bloodpressure_payload(user):
    """Create blood pressure measurements (2-3 times per day)"""
    # Profile-based BP ranges
    bp_ranges = {
        "active_male": {"systolic": (115, 125), "diastolic": (72, 80)},
        "moderate_female": {"systolic": (110, 120), "diastolic": (70, 78)}
    }
    bp = bp_ranges[user["profile"]]
    
    measurements = [
        {"time": get_timestamp_nano(8, 0), "context": "morning"},
        {"time": get_timestamp_nano(14, 0), "context": "afternoon"},
        {"time": get_timestamp_nano(20, 0), "context": "evening"}
    ]
    
    metrics = []
    for meas in measurements:
        systolic = random.randint(*bp["systolic"])
        diastolic = random.randint(*bp["diastolic"])
        
        metrics.extend([
            {
                "name": "health.bloodpressure.systolic",
                "description": "Systolic blood pressure",
                "unit": "mm[Hg]",
                "data": {
                    "data_points": [{
                        "attributes": {"measurement_context": meas["context"]},
                        "start_time_unix_nano": None,
                        "time_unix_nano": meas["time"],
                        "value": float(systolic)
                    }]
                }
            },
            {
                "name": "health.bloodpressure.diastolic",
                "description": "Diastolic blood pressure",
                "unit": "mm[Hg]",
                "data": {
                    "data_points": [{
                        "attributes": {"measurement_context": meas["context"]},
                        "start_time_unix_nano": None,
                        "time_unix_nano": meas["time"],
                        "value": float(diastolic)
                    }]
                }
            }
        ])
    
    return {
        "request_id": f"req-bp-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": metrics
    }

def create_glucose_payload(user):
    """Create blood glucose measurements"""
    # Normal glucose range: 70-100 mg/dL fasting, <140 mg/dL post-meal
    measurements = [
        {"time": get_timestamp_nano(7, 30), "type": "fasting", "range": (75, 95)},
        {"time": get_timestamp_nano(9, 30), "type": "post_meal", "range": (110, 135)},
        {"time": get_timestamp_nano(13, 30), "type": "post_meal", "range": (105, 130)},
        {"time": get_timestamp_nano(19, 30), "type": "post_meal", "range": (100, 125)}
    ]
    
    metrics = []
    for meas in measurements:
        glucose = random.randint(*meas["range"])
        metric_name = f"health.glucose.{meas['type']}" if meas['type'] != "level" else "health.glucose.level"
        
        metrics.append({
            "name": metric_name,
            "description": f"Blood glucose - {meas['type']}",
            "unit": "mg/dL",
            "data": {
                "data_points": [{
                    "attributes": {"measurement_type": meas["type"]},
                    "start_time_unix_nano": None,
                    "time_unix_nano": meas["time"],
                    "value": float(glucose)
                }]
            }
        })
    
    return {
        "request_id": f"req-glucose-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": metrics
    }

def create_spo2_payload(user):
    """Create SpO2 (blood oxygen) measurements"""
    # Normal SpO2: 95-100%
    data_points = []
    
    # Measure every 2 hours during waking hours
    for hour in range(8, 23, 2):
        spo2 = random.randint(96, 99)
        data_points.append({
            "attributes": {},
            "start_time_unix_nano": None,
            "time_unix_nano": get_timestamp_nano(hour, 0),
            "value": float(spo2)
        })
    
    return {
        "request_id": f"req-spo2-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": [
            {
                "name": "health.spo2.percentage",
                "description": "Blood oxygen saturation",
                "unit": "%",
                "data": {"data_points": data_points}
            }
        ]
    }

def create_workout_payload(user):
    """Create workout session metrics"""
    # Profile-based workout intensity
    workout_params = {
        "active_male": {
            "duration": random.randint(2700, 3600),  # 45-60 min
            "distance": random.randint(6000, 8000),  # 6-8 km
            "calories": random.randint(450, 600),
            "type": "running"
        },
        "moderate_female": {
            "duration": random.randint(1800, 2700),  # 30-45 min
            "distance": random.randint(4000, 6000),  # 4-6 km
            "calories": random.randint(300, 450),
            "type": "jogging"
        }
    }
    params = workout_params[user["profile"]]
    
    workout_start = get_timestamp_nano(18, 0)
    workout_end = get_timestamp_nano(18, 0) + (params["duration"] * 1000000000)
    
    return {
        "request_id": f"req-workout-{user['device_id']}-{int(time.time())}",
        "resource": {
            "attributes": {
                "device_id": user["device_id"],
                "device_type": user["device_type"],
                "device_manufacturer": user["device_manufacturer"],
                "device_model": user["device_model"],
                "user_id": user["user_id"],
                "app_version": "2.1.0"
            }
        },
        "scope": {
            "name": "health.metrics.collector",
            "version": "1.0.0"
        },
        "metrics": [
            {
                "name": "health.workout.duration",
                "description": "Workout duration",
                "unit": "s",
                "data": {
                    "data_points": [{
                        "attributes": {"workout_type": params["type"]},
                        "start_time_unix_nano": workout_start,
                        "time_unix_nano": workout_end,
                        "value": float(params["duration"])
                    }]
                }
            },
            {
                "name": "health.workout.distance",
                "description": "Distance covered",
                "unit": "m",
                "data": {
                    "data_points": [{
                        "attributes": {"workout_type": params["type"]},
                        "start_time_unix_nano": workout_start,
                        "time_unix_nano": workout_end,
                        "value": float(params["distance"])
                    }]
                }
            },
            {
                "name": "health.workout.calories",
                "description": "Calories burned",
                "unit": "kcal",
                "data": {
                    "data_points": [{
                        "attributes": {"workout_type": params["type"]},
                        "start_time_unix_nano": workout_start,
                        "time_unix_nano": workout_end,
                        "value": float(params["calories"])
                    }]
                }
            }
        ]
    }

def main():
    """Generate all sample data files"""
    output_dir = Path(__file__).parent.parent / "sample_data"
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 70)
    print("Generating Sample Health Metrics Data")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print(f"Base timestamp: {BASE_TIME.isoformat()}Z\n")
    
    for user in USERS:
        print(f"\nGenerating data for: {user['user_id']}")
        print("-" * 70)
        
        user_dir = output_dir / user["device_id"]
        user_dir.mkdir(exist_ok=True)
        
        # Generate activity data
        activity_data = generate_activity_data(user, 0, 24)
        activity_payload = create_activity_payload(user, activity_data)
        with open(user_dir / "activity.json", "w") as f:
            json.dump(activity_payload, f, indent=2)
        print(f"  ✓ activity.json ({len(activity_payload['metrics'])} metrics)")
        
        # Generate heart rate data
        heartrate_payload = create_heartrate_payload(user)
        with open(user_dir / "heartrate.json", "w") as f:
            json.dump(heartrate_payload, f, indent=2)
        print(f"  ✓ heartrate.json ({len(heartrate_payload['metrics'])} metrics)")
        
        # Generate sleep data
        sleep_payload = create_sleep_payload(user)
        with open(user_dir / "sleep.json", "w") as f:
            json.dump(sleep_payload, f, indent=2)
        print(f"  ✓ sleep.json ({len(sleep_payload['metrics'])} metrics)")
        
        # Generate blood pressure data
        bp_payload = create_bloodpressure_payload(user)
        with open(user_dir / "bloodpressure.json", "w") as f:
            json.dump(bp_payload, f, indent=2)
        print(f"  ✓ bloodpressure.json ({len(bp_payload['metrics'])} metrics)")
        
        # Generate glucose data
        glucose_payload = create_glucose_payload(user)
        with open(user_dir / "glucose.json", "w") as f:
            json.dump(glucose_payload, f, indent=2)
        print(f"  ✓ glucose.json ({len(glucose_payload['metrics'])} metrics)")
        
        # Generate SpO2 data
        spo2_payload = create_spo2_payload(user)
        with open(user_dir / "spo2.json", "w") as f:
            json.dump(spo2_payload, f, indent=2)
        print(f"  ✓ spo2.json ({len(spo2_payload['metrics'])} metrics)")
        
        # Generate workout data
        workout_payload = create_workout_payload(user)
        with open(user_dir / "workout.json", "w") as f:
            json.dump(workout_payload, f, indent=2)
        print(f"  ✓ workout.json ({len(workout_payload['metrics'])} metrics)")
    
    print("\n" + "=" * 70)
    print("✓ Sample data generation complete!")
    print(f"\nGenerated files in: {output_dir}")
    print("\nDirectory structure:")
    print("  sample_data/")
    for user in USERS:
        print(f"    {user['device_id']}/")
        print("      ├── activity.json")
        print("      ├── heartrate.json")
        print("      ├── sleep.json")
        print("      ├── bloodpressure.json")
        print("      ├── glucose.json")
        print("      ├── spo2.json")
        print("      └── workout.json")

if __name__ == "__main__":
    main()

# Made with Bob
