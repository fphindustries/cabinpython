# Cloudflare API Schema Update Guide

## Overview
This guide documents the required changes to your Cloudflare Workers API to support the new sensor data fields.

## API Endpoint
The data is sent to: `https://cabinpi.com/api/sensors/ingest`

## New Fields in SensorData Schema

The following fields have been added to the API payload:

### Indoor Sensor Data (SHT45)
| Field Name | Type | Description | Units | Example |
|-----------|------|-------------|-------|---------|
| `intC` | number (optional) | Indoor temperature | Celsius | 21.5 |
| `intF` | number (optional) | Indoor temperature | Fahrenheit | 70.7 |
| `humidity` | number (optional) | Indoor relative humidity | Percent | 45.2 |

**Note**: The field names remain the same as before, but now populated by SHT45 instead of SHT31.

### DC Power Monitor Data (INA228)
| Field Name | Type | Description | Units | Example |
|-----------|------|-------------|-------|---------|
| `dcBusVoltage` | number (optional) | DC system bus voltage | Volts | 13.2 |
| `dcCurrent` | number (optional) | DC current draw | Amperes | 5.4 |
| `dcPower` | number (optional) | DC power consumption | Watts | 71.28 |
| `dcShuntVoltage` | number (optional) | Shunt resistor voltage drop | Millivolts | 0.081 |

### Basement Temperature Data (DS18B20)
| Field Name | Type | Description | Units | Example |
|-----------|------|-------------|-------|---------|
| `basementC` | number (optional) | Basement temperature | Celsius | 15.3 |
| `basementF` | number (optional) | Basement temperature | Fahrenheit | 59.5 |

## Updated TypeScript/Zod Schema

If your Cloudflare Worker uses Zod for validation, update your schema:

```typescript
import { z } from 'zod';

const SensorDataSchema = z.object({
  date: z.string().datetime(),

  // Solar charge controller data
  ampHours: z.number().optional(),
  batteryState: z.number().optional(),
  chargeState: z.number().optional(),
  classicState: z.number().optional(),
  dispavgVbatt: z.number().optional(),
  dispavgVpv: z.number().optional(),
  ibattDisplay: z.number().optional(),
  kwhours: z.number().optional(),
  niteMinutesNoPwr: z.number().optional(),
  pvInputCurrent: z.number().optional(),
  vocLastMeasured: z.number().optional(),
  watts: z.number().optional(),

  // Indoor sensor data (SHT45)
  intC: z.number().optional(),
  intF: z.number().optional(),
  humidity: z.number().optional(),

  // DC Power Monitor data (INA228) - NEW
  dcBusVoltage: z.number().optional(),
  dcCurrent: z.number().optional(),
  dcPower: z.number().optional(),
  dcShuntVoltage: z.number().optional(),

  // Basement temperature (DS18B20) - NEW
  basementC: z.number().optional(),
  basementF: z.number().optional(),

  // External weather data
  avgStrikeDistance: z.number().optional(),
  dailyAccumulation: z.number().optional(),
  extF: z.number().optional(),
  extHumidity: z.number().optional(),
  illuminance: z.number().optional(),
  inHg: z.number().optional(),
  rain: z.number().optional(),
  solarRadiation: z.number().optional(),
  strikeCount: z.number().optional(),
  uv: z.number().optional(),
  windAvg: z.number().optional(),
  windDirection: z.number().optional(),
  windGust: z.number().optional(),

  // Inverter data
  inverterAacOut: z.number().optional(),
  inverterFault: z.number().optional(),
  inverterMode: z.number().optional(),
  inverterOn: z.number().optional(),
  inverterVacOut: z.number().optional(),
});

const IngestRequestSchema = z.object({
  records: z.array(SensorDataSchema),
});

type SensorData = z.infer<typeof SensorDataSchema>;
type IngestRequest = z.infer<typeof IngestRequestSchema>;
```

## Updated OpenAPI Specification

If you maintain an OpenAPI spec, add these fields to the `SensorData` component:

```yaml
components:
  schemas:
    SensorData:
      type: object
      required:
        - date
      properties:
        date:
          type: string
          format: date-time
          description: ISO 8601 timestamp

        # ... existing fields ...

        # Indoor sensor data (SHT45)
        intC:
          type: number
          description: Indoor temperature in Celsius (SHT45)
          example: 21.5
        intF:
          type: number
          description: Indoor temperature in Fahrenheit (SHT45)
          example: 70.7
        humidity:
          type: number
          description: Indoor relative humidity percentage (SHT45)
          minimum: 0
          maximum: 100
          example: 45.2

        # DC Power Monitor (INA228)
        dcBusVoltage:
          type: number
          description: DC system bus voltage in volts (INA228)
          example: 13.2
        dcCurrent:
          type: number
          description: DC current in amperes (INA228)
          example: 5.4
        dcPower:
          type: number
          description: DC power in watts (INA228)
          example: 71.28
        dcShuntVoltage:
          type: number
          description: Shunt voltage in millivolts (INA228)
          example: 0.081

        # Basement Temperature (DS18B20)
        basementC:
          type: number
          description: Basement temperature in Celsius (DS18B20)
          example: 15.3
        basementF:
          type: number
          description: Basement temperature in Fahrenheit (DS18B20)
          example: 59.5
```

## Database Schema Update (D1/KV/etc.)

If your Cloudflare Worker stores data in D1 or another database, update your table schema:

### D1 SQL Migration

```sql
-- Add new columns to sensor_data table
ALTER TABLE sensor_data ADD COLUMN dc_bus_voltage REAL;
ALTER TABLE sensor_data ADD COLUMN dc_current REAL;
ALTER TABLE sensor_data ADD COLUMN dc_power REAL;
ALTER TABLE sensor_data ADD COLUMN dc_shunt_voltage REAL;
ALTER TABLE sensor_data ADD COLUMN basement_c REAL;
ALTER TABLE sensor_data ADD COLUMN basement_f REAL;
ALTER TABLE sensor_data ADD COLUMN int_c REAL;  -- if not already exists
```

### Example INSERT Statement Update

```sql
INSERT INTO sensor_data (
  date,
  -- Solar fields
  dispavg_vbatt, watts,
  -- Indoor fields
  int_c, int_f, humidity,
  -- DC Power fields (NEW)
  dc_bus_voltage, dc_current, dc_power, dc_shunt_voltage,
  -- Basement fields (NEW)
  basement_c, basement_f,
  -- Weather fields
  ext_f, ext_humidity
  -- ... other fields ...
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ...);
```

## Example API Request

Here's what a complete request will look like:

```json
{
  "records": [
    {
      "date": "2025-12-26T10:30:00Z",
      "dispavgVbatt": 13.2,
      "watts": 245,
      "intC": 21.5,
      "intF": 70.7,
      "humidity": 45.2,
      "dcBusVoltage": 13.2,
      "dcCurrent": 5.4,
      "dcPower": 71.28,
      "dcShuntVoltage": 0.081,
      "basementC": 15.3,
      "basementF": 59.5,
      "extF": 42.3,
      "extHumidity": 65.0,
      "windAvg": 5.2,
      "inverterOn": 1,
      "inverterMode": 2
    }
  ]
}
```

## Testing the API Changes

### 1. Test with curl

```bash
curl -X POST https://cabinpi.com/api/sensors/ingest \
  -H "CF-Access-Client-Id: YOUR_CLIENT_ID" \
  -H "CF-Access-Client-Secret: YOUR_CLIENT_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "records": [{
      "date": "2025-12-26T10:30:00Z",
      "intC": 21.5,
      "intF": 70.7,
      "humidity": 45.2,
      "dcBusVoltage": 13.2,
      "dcCurrent": 5.4,
      "dcPower": 71.28,
      "basementC": 15.3,
      "basementF": 59.5,
      "dispavgVbatt": 13.2,
      "watts": 245
    }]
  }'
```

### 2. Test from Python

```python
import requests

url = "https://cabinpi.com/api/sensors/ingest"
headers = {
    "CF-Access-Client-Id": "YOUR_CLIENT_ID",
    "CF-Access-Client-Secret": "YOUR_CLIENT_SECRET",
    "Content-Type": "application/json"
}
payload = {
    "records": [{
        "date": "2025-12-26T10:30:00Z",
        "intC": 21.5,
        "dcBusVoltage": 13.2,
        "dcCurrent": 5.4,
        "dcPower": 71.28,
        "basementC": 15.3,
        "basementF": 59.5
    }]
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code, response.json())
```

## Deployment Steps

### 1. Update Worker Code
Deploy the updated schema definition to your Cloudflare Worker.

### 2. Test Endpoint
Use the curl or Python examples above to verify the endpoint accepts the new fields.

### 3. Update Database Schema
If using D1 or another database, run the migration scripts.

### 4. Deploy Client Updates
Once the API is updated and tested, deploy the updated `capture_measurements.py` script.

### 5. Monitor
Watch for errors in both Cloudflare Worker logs and client-side logs:

```bash
# Cloudflare Workers logs
wrangler tail

# Client logs
journalctl -u cabin-measurements.service -f
```

## Backward Compatibility

All new fields are **optional**, ensuring backward compatibility:
- Old clients that don't send the new fields will continue to work
- The API will accept and store `null` values for missing fields
- Existing data without these fields remains valid

## Field Mapping Reference

| Database Column | API Field (camelCase) | Sensor | Description |
|----------------|----------------------|--------|-------------|
| int_c | intC | SHT45 | Indoor temp (°C) |
| int_f | intF | SHT45 | Indoor temp (°F) |
| humidity | humidity | SHT45 | Indoor humidity (%) |
| dc_bus_voltage | dcBusVoltage | INA228 | Bus voltage (V) |
| dc_current | dcCurrent | INA228 | Current (A) |
| dc_power | dcPower | INA228 | Power (W) |
| dc_shunt_voltage | dcShuntVoltage | INA228 | Shunt voltage (mV) |
| basement_c | basementC | DS18B20 | Basement temp (°C) |
| basement_f | basementF | DS18B20 | Basement temp (°F) |

## Troubleshooting

### Issue: Validation errors on new fields
**Solution**: Ensure the Zod schema or validation layer includes the new optional fields.

### Issue: Data not appearing in database
**Solution**: Verify the database columns were added and the INSERT statement includes the new fields.

### Issue: 400 Bad Request
**Solution**: Check that field names use exact camelCase as specified (e.g., `dcBusVoltage`, not `dc_bus_voltage`).

### Issue: Cloudflare Access blocking requests
**Solution**: Verify the `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers are correct.

## Rollback Plan

If issues arise, the new fields can be ignored server-side without breaking compatibility:

```typescript
// Temporarily ignore new fields while investigating issues
const { dcBusVoltage, dcCurrent, dcPower, dcShuntVoltage,
        basementC, basementF, intC, ...safeData } = receivedData;

// Process only the old fields
await processData(safeData);
```

Or remove the columns from the database:

```sql
ALTER TABLE sensor_data DROP COLUMN dc_bus_voltage;
ALTER TABLE sensor_data DROP COLUMN dc_current;
ALTER TABLE sensor_data DROP COLUMN dc_power;
ALTER TABLE sensor_data DROP COLUMN dc_shunt_voltage;
ALTER TABLE sensor_data DROP COLUMN basement_c;
ALTER TABLE sensor_data DROP COLUMN basement_f;
```
