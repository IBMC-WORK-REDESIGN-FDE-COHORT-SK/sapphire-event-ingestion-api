# Sample Health Metrics Data

This directory contains realistic sample health metrics data for testing the Sapphire Event Ingestion API.

## Overview

Sample data has been generated for **2 users** covering a **full day** (24 hours) of health metrics:

### Users

1. **Michael Davis** (`michael.davis@sapphirewellness.com`)
   - Device: Apple Watch Series 9 (`apple-watch-md-001`)
   - Profile: Active male
   - Higher activity levels, more intense workouts

2. **Sarah Johnson** (`sarah.johnson@sapphirewellness.com`)
   - Device: Fitbit Charge 6 (`fitbit-sj-002`)
   - Profile: Moderate female
   - Moderate activity levels, balanced lifestyle

## Data Generated

Each user has 7 JSON files representing different metric types:

### 1. Activity Metrics (`activity.json`)
- **Metrics**: Steps, distance, calories
- **Frequency**: Every 30 minutes (48 data points per day)
- **Realistic patterns**:
  - Low activity during sleep (22:00-06:00)
  - Morning routine spike (07:00-09:00)
  - Lunch walk (12:00-13:00)
  - Evening exercise (17:00-19:00)
  - Regular activity throughout the day

### 2. Heart Rate (`heartrate.json`)
- **Metrics**: Continuous BPM, resting HR, max HR
- **Frequency**: Every 5 minutes during waking hours (6 AM - 11 PM)
- **Realistic ranges**:
  - Michael: Resting 58-65, Active 120-160, Max ~185
  - Sarah: Resting 62-70, Active 110-145, Max ~175
- **Patterns**: Higher during exercise, lower during rest

### 3. Sleep Data (`sleep.json`)
- **Metrics**: Duration, deep sleep, light sleep, REM, awake time, quality score
- **Sleep period**: 11 PM - 7 AM (8 hours)
- **Realistic distribution**:
  - Deep sleep: 15-20% of total
  - REM sleep: 20-25% of total
  - Light sleep: 50-55% of total
  - Awake: Remainder
- **Quality scores**: 75-88 (good sleep quality)

### 4. Blood Pressure (`bloodpressure.json`)
- **Metrics**: Systolic, diastolic
- **Frequency**: 3 times per day (morning, afternoon, evening)
- **Realistic ranges**:
  - Michael: 115-125 / 72-80 mmHg
  - Sarah: 110-120 / 70-78 mmHg

### 5. Blood Glucose (`glucose.json`)
- **Metrics**: Fasting, post-meal levels
- **Frequency**: 4 times per day
- **Realistic ranges**:
  - Fasting: 75-95 mg/dL
  - Post-meal: 100-135 mg/dL

### 6. SpO2 / Blood Oxygen (`spo2.json`)
- **Metrics**: Oxygen saturation percentage
- **Frequency**: Every 2 hours during waking hours
- **Realistic range**: 96-99%

### 7. Workout Session (`workout.json`)
- **Metrics**: Duration, distance, calories
- **Time**: Evening workout (6:00 PM)
- **Realistic values**:
  - Michael: 45-60 min running, 6-8 km, 450-600 kcal
  - Sarah: 30-45 min jogging, 4-6 km, 300-450 kcal

## Directory Structure

```
sample_data/
├── README.md (this file)
├── apple-watch-md-001/          # Michael Davis
│   ├── activity.json
│   ├── heartrate.json
│   ├── sleep.json
│   ├── bloodpressure.json
│   ├── glucose.json
│   ├── spo2.json
│   └── workout.json
└── fitbit-sj-002/               # Sarah Johnson
    ├── activity.json
    ├── heartrate.json
    ├── sleep.json
    ├── bloodpressure.json
    ├── glucose.json
    ├── spo2.json
    └── workout.json
```

## Generating Sample Data

To regenerate the sample data:

```bash
python scripts/generate_sample_data.py
```

This will:
- Generate fresh data with current timestamps
- Create realistic patterns based on time of day
- Apply user-specific profiles (active vs moderate)
- Output formatted JSON files ready for ingestion

## Ingesting Sample Data

### Prerequisites

1. **API must be running**:
   ```bash
   python run.py
   # or
   podman-compose up -d sapphire-event-ingestion-api
   ```

2. **Get a JWT token** from Keycloak:
   ```bash
   curl -X POST http://localhost:8090/realms/saphhire-ui/protocol/openid-connect/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials" \
     -d "client_id=sapphire-event-ingestion" \
     -d "client_secret=YOUR_CLIENT_SECRET"
   ```

### Method 1: Using the Ingestion Script (Recommended)

```bash
# Set the bearer token
export BEARER_TOKEN="your_jwt_token_here"

# Run the ingestion script
python scripts/ingest_sample_data.py
```

The script will:
- ✅ Automatically find all sample JSON files
- ✅ Display a summary before ingesting
- ✅ Ingest files with proper delays
- ✅ Show progress and results
- ✅ Provide a detailed summary

### Method 2: Manual Ingestion

```bash
# Set variables
TOKEN="your_jwt_token_here"
API_URL="http://localhost:8000/v1/metrics/ingest"

# Ingest a single file
curl -X POST $API_URL \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @sample_data/apple-watch-md-001/activity.json
```

## Verifying Ingestion

### 1. Check API Response
Successful ingestion returns:
```json
{
  "request_id": "req-activity-...",
  "status": "accepted",
  "accepted_count": 30,
  "rejected_count": 0,
  "timestamp": "2026-01-29T07:00:00Z"
}
```

### 2. View in Kafka UI
1. Open: http://localhost:8080
2. Navigate to Topics
3. Select a topic (e.g., `health.metrics.activity`)
4. View messages with Avro deserialization

### 3. Check Kafka Topics
```bash
# List topics
curl http://localhost:8080/api/clusters/local/topics

# Expected topics:
# - health.metrics.activity
# - health.metrics.heartrate
# - health.metrics.sleep
# - health.metrics.bloodpressure
# - health.metrics.glucose
# - health.metrics.spo2
# - health.metrics.workout
```

## Data Characteristics

### Timestamps
- All timestamps are in **Unix nanoseconds** (19 digits)
- Based on current UTC time
- Realistic time-of-day patterns

### Realistic Patterns
- **Circadian rhythms**: Activity varies by time of day
- **Sleep cycles**: Proper distribution of sleep stages
- **Exercise impact**: Heart rate spikes during workouts
- **Meal timing**: Glucose measurements around meal times
- **Individual differences**: Michael (active) vs Sarah (moderate)

### Data Volume
- **Total files**: 14 (7 per user)
- **Total metrics**: ~200+ individual metric data points
- **Total messages**: ~14 Kafka messages (one per file)
- **Data size**: ~50-100 KB per user

## Troubleshooting

### "No sample data files found"
Run the generation script first:
```bash
python scripts/generate_sample_data.py
```

### "Connection error"
Ensure the API is running:
```bash
curl http://localhost:8000/v1/health
```

### "Authentication failed"
Check your JWT token:
- Token must be valid (not expired)
- Token must be from the correct Keycloak realm
- Use the full token (starts with `eyJ...`)

### "Validation failed"
Timestamps might be too old. Regenerate data:
```bash
python scripts/generate_sample_data.py
```

## Next Steps

After ingesting the sample data:

1. **Explore Kafka UI**: View messages in different topics
2. **Verify schemas**: Check that Avro deserialization works
3. **Build consumers**: Create services to process the metrics
4. **Create dashboards**: Visualize the health data
5. **Test analytics**: Run queries on the ingested data

## Notes

- Data is generated with realistic values but is **synthetic**
- Timestamps are relative to generation time
- User profiles are fictional
- Metric ranges follow medical guidelines
- Data patterns simulate real-world usage

---

**Generated by**: Sapphire Event Ingestion API  
**Last updated**: 2026-01-29