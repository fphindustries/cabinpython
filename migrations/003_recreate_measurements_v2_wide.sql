-- Recreate measurements_v2 with wide table format for React dashboard compatibility
-- This replaces the JSON-based structure with queryable columns

USE cabinpi;

-- Drop the existing JSON-based table
DROP TABLE IF EXISTS measurements_v2;

-- Create wide table with all sensor fields
CREATE TABLE measurements_v2 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME(6) NOT NULL,

    -- Indoor Environmental (SHT45/SHT31)
    indoor_temp_c DECIMAL(5,2),
    indoor_temp_f DECIMAL(5,2),
    indoor_humidity DECIMAL(5,2),

    -- Solar Charge Controller (Modbus)
    solar_absorb_time SMALLINT UNSIGNED,
    solar_amp_hours SMALLINT UNSIGNED,
    solar_equalize_time SMALLINT UNSIGNED,
    solar_float_time SMALLINT UNSIGNED,
    solar_highest_input_voltage DECIMAL(5,2),
    solar_battery_current DECIMAL(6,2),
    solar_nite_minutes_no_power SMALLINT,
    solar_pv_input_current DECIMAL(6,2),
    solar_voc_last_measured DECIMAL(5,2),
    solar_battery_state TINYINT,
    solar_charge_state SMALLINT,
    solar_classic_state TINYINT,
    solar_battery_voltage DECIMAL(5,2),
    solar_pv_voltage DECIMAL(5,2),
    solar_kwh DECIMAL(7,3),
    solar_power_watts SMALLINT,
    solar_battery_temp_c DECIMAL(5,2),
    solar_battery_temp_f DECIMAL(5,2),
    solar_lifetime_kwh DECIMAL(10,3),
    solar_lifetime_amp_hours DECIMAL(10,2),

    -- Outdoor Weather (WeatherFlow API)
    outdoor_temp_c DECIMAL(5,2),
    outdoor_temp_f DECIMAL(5,2),
    outdoor_humidity DECIMAL(5,2),
    outdoor_pressure_hpa DECIMAL(6,2),
    outdoor_pressure_inhg DECIMAL(5,2),
    outdoor_wind_avg DECIMAL(5,2),
    outdoor_wind_gust DECIMAL(5,2),
    outdoor_wind_direction SMALLINT,
    outdoor_illuminance INT,
    outdoor_uv DECIMAL(4,2),
    outdoor_solar_radiation INT,
    outdoor_rain DECIMAL(6,2),
    outdoor_daily_accumulation DECIMAL(6,2),
    outdoor_strike_distance DECIMAL(6,2),
    outdoor_strike_count INT,
    outdoor_station_battery DECIMAL(4,2),

    -- Magnum Inverter (RS-485 or pymagnum)
    inverter_on TINYINT(1),
    inverter_mode SMALLINT,
    inverter_fault SMALLINT,
    inverter_vac_out DECIMAL(5,2),
    inverter_aac_out DECIMAL(6,2),
    inverter_vdc DECIMAL(5,2),
    inverter_battery_temp_c DECIMAL(5,2),
    inverter_battery_temp_f DECIMAL(5,2),

    -- INA228 Power Monitor (Battery)
    battery_voltage_v DECIMAL(6,3),
    battery_current_a DECIMAL(7,3),
    battery_current_ma DECIMAL(8,2),
    battery_power_w DECIMAL(8,3),
    battery_power_mw DECIMAL(9,2),
    battery_shunt_voltage_mv DECIMAL(7,3),
    battery_temp_c DECIMAL(5,2),
    battery_temp_f DECIMAL(5,2),

    -- INA228 Power Monitor (Solar Panel)
    solar_panel_voltage_v DECIMAL(6,3),
    solar_panel_current_a DECIMAL(7,3),
    solar_panel_current_ma DECIMAL(8,2),
    solar_panel_power_w DECIMAL(8,3),
    solar_panel_power_mw DECIMAL(9,2),
    solar_panel_shunt_voltage_mv DECIMAL(7,3),
    solar_panel_temp_c DECIMAL(5,2),
    solar_panel_temp_f DECIMAL(5,2),

    -- DS18B20 1-Wire Temperature Sensors
    outdoor_sensor_temp_c DECIMAL(6,3),
    outdoor_sensor_temp_f DECIMAL(5,2),
    outdoor_sensor_device_id VARCHAR(20),

    -- Additional DS18B20 sensors (if you add more)
    temp_sensor_2_c DECIMAL(6,3),
    temp_sensor_2_f DECIMAL(5,2),
    temp_sensor_2_device_id VARCHAR(20),
    temp_sensor_2_label VARCHAR(50),

    temp_sensor_3_c DECIMAL(6,3),
    temp_sensor_3_f DECIMAL(5,2),
    temp_sensor_3_device_id VARCHAR(20),
    temp_sensor_3_label VARCHAR(50),

    -- System/Meta columns
    synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for performance
    INDEX idx_timestamp (timestamp),
    INDEX idx_synced (synced),
    INDEX idx_created_at (created_at),
    INDEX idx_timestamp_synced (timestamp, synced)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='Sensor measurements v2 - wide table format for React dashboard';

-- Display confirmation
SELECT 'measurements_v2 table recreated with wide format!' as status;
DESCRIBE measurements_v2;
