-- Add aggregated inverter columns to measurements_v2
-- These columns store min/max/avg values for continuous inverter monitoring

USE cabinpi;

-- Add charger LED status
ALTER TABLE measurements_v2
ADD COLUMN charger_on TINYINT(1) AFTER inverter_on;

-- Add inverter mode name
ALTER TABLE measurements_v2
ADD COLUMN inverter_mode_name VARCHAR(20) AFTER inverter_mode;

-- Add VDC aggregates (min/max already exist as vdc, add aggregates)
ALTER TABLE measurements_v2
ADD COLUMN inverter_vdc_min DECIMAL(5,2) AFTER inverter_vdc,
ADD COLUMN inverter_vdc_max DECIMAL(5,2) AFTER inverter_vdc_min;

-- Add VACout aggregates
ALTER TABLE measurements_v2
ADD COLUMN inverter_vac_out_min DECIMAL(5,2) AFTER inverter_vac_out,
ADD COLUMN inverter_vac_out_max DECIMAL(5,2) AFTER inverter_vac_out_min;

-- Add VACin and aggregates
ALTER TABLE measurements_v2
ADD COLUMN inverter_vac_in DECIMAL(5,2) AFTER inverter_battery_temp_f,
ADD COLUMN inverter_vac_in_min DECIMAL(5,2) AFTER inverter_vac_in,
ADD COLUMN inverter_vac_in_max DECIMAL(5,2) AFTER inverter_vac_in_min;

-- Add AACout aggregates
ALTER TABLE measurements_v2
ADD COLUMN inverter_aac_out_min DECIMAL(6,2) AFTER inverter_aac_out,
ADD COLUMN inverter_aac_out_max DECIMAL(6,2) AFTER inverter_aac_out_min;

-- Add AACin and aggregates
ALTER TABLE measurements_v2
ADD COLUMN inverter_aac_in DECIMAL(6,2) AFTER inverter_aac_out_max,
ADD COLUMN inverter_aac_in_min DECIMAL(6,2) AFTER inverter_aac_in,
ADD COLUMN inverter_aac_in_max DECIMAL(6,2) AFTER inverter_aac_in_min;

-- Add battery temperature aggregates (avg already exists, add min/max)
ALTER TABLE measurements_v2
ADD COLUMN inverter_battery_temp_c_min DECIMAL(5,2) AFTER inverter_battery_temp_c,
ADD COLUMN inverter_battery_temp_c_max DECIMAL(5,2) AFTER inverter_battery_temp_c_min;

-- Add transformer temperature and aggregates
ALTER TABLE measurements_v2
ADD COLUMN inverter_transformer_temp_c DECIMAL(5,2) AFTER inverter_battery_temp_c_max,
ADD COLUMN inverter_transformer_temp_c_min DECIMAL(5,2) AFTER inverter_transformer_temp_c,
ADD COLUMN inverter_transformer_temp_c_max DECIMAL(5,2) AFTER inverter_transformer_temp_c_min;

-- Add FET temperature and aggregates
ALTER TABLE measurements_v2
ADD COLUMN inverter_fet_temp_c DECIMAL(5,2) AFTER inverter_transformer_temp_c_max,
ADD COLUMN inverter_fet_temp_c_min DECIMAL(5,2) AFTER inverter_fet_temp_c,
ADD COLUMN inverter_fet_temp_c_max DECIMAL(5,2) AFTER inverter_fet_temp_c_min;

-- Display confirmation
SELECT 'Inverter aggregate columns added successfully!' as status;

-- Show updated column count
SELECT COUNT(*) as column_count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='cabinpi' AND TABLE_NAME='measurements_v2';
