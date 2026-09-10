"""
Common functions for syncing sensor data to the remote API.

This module provides shared functionality used by both capture_measurements.py
and sync_to_cloudflare.py to send data to the Cloudflare-protected API.
"""

import logging
import configparser
import mysql.connector
import requests
from typing import List, Dict


def get_unsynced_measurements(config: configparser.ConfigParser, limit: int = 10) -> List[Dict]:
    """
    Fetch unsynced measurements from the database.

    Args:
        config: Configuration object with database credentials
        limit: Maximum number of records to fetch

    Returns:
        List of measurement dictionaries
    """
    try:
        username = config.get('Database', 'username')
        password = config.get('Database', 'password')
        database = config.get('Database', 'database')

        conn = mysql.connector.connect(
            host="localhost",
            database=database,
            user=username,
            password=password
        )

        cursor = conn.cursor(dictionary=True)

        # Fetch unsynced records (or all records if synced column doesn't exist)
        # Using Date as primary key
        try:
            query = """
                SELECT * FROM measurements
                WHERE synced = 0
                ORDER BY Date ASC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
        except mysql.connector.Error:
            # If synced column doesn't exist, just get the most recent records
            logging.warning("synced column not found, fetching most recent records")
            query = """
                SELECT * FROM measurements
                ORDER BY Date DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))

        records = cursor.fetchall()

        cursor.close()
        conn.close()

        return records

    except Exception:
        logging.exception("Error fetching unsynced measurements from database")
        return []


def mark_as_synced(config: configparser.ConfigParser, record_date) -> bool:
    """
    Mark a measurement record as synced in the database.

    Args:
        config: Configuration object with database credentials
        record_date: The Date (primary key) of the record to mark as synced

    Returns:
        True if successful, False otherwise
    """
    try:
        username = config.get('Database', 'username')
        password = config.get('Database', 'password')
        database = config.get('Database', 'database')

        conn = mysql.connector.connect(
            host="localhost",
            database=database,
            user=username,
            password=password
        )

        cursor = conn.cursor()

        update_query = "UPDATE measurements SET synced = 1 WHERE Date = %s"
        cursor.execute(update_query, (record_date,))
        conn.commit()

        cursor.close()
        conn.close()

        return True

    except Exception:
        logging.exception("Error marking record %s as synced", record_date)
        return False


def convert_measurement_to_d1_row(record: Dict) -> Dict:
    """
    Convert a database record to the row format expected by the Cloudflare D1
    `measurements` table (flat structure with camelCase column names).

    Args:
        record: Database record dictionary

    Returns:
        Dictionary keyed by D1 column name
    """
    # Convert datetime to ISO format string if needed
    date_value = record.get('Date')
    if date_value:
        date_value = date_value.isoformat() if hasattr(date_value, 'isoformat') else str(date_value)

    # Build the API payload matching the SensorData schema
    # Note: Using flat structure with camelCase as per OpenAPI spec
    payload = {
        "date": date_value,
        # Solar charge controller data
        "ampHours": record.get('AmpHours'),
        "batteryState": record.get('BatteryState'),
        "chargeState": record.get('ChargeState'),
        "classicState": record.get('ClassicState'),
        "dispavgVbatt": record.get('DispavgVbatt'),
        "dispavgVpv": record.get('DispavgVpv'),
        "ibattDisplay": record.get('IbattDisplay'),
        "kwhours": record.get('kWHours'),
        "niteMinutesNoPwr": record.get('NiteMinutesNoPwr'),
        "pvInputCurrent": record.get('PvInputCurrent'),
        "vocLastMeasured": record.get('VocLastMeasured'),
        "watts": record.get('Watts'),
        # Indoor sensor data (SHT45)
        "intF": record.get('Int_F'),
        #"intC": record.get('int_c'),
        "humidity": record.get('Humidity'),
        # DC Power Monitor data (INA228)
        "dcBusVoltage": record.get('dc_bus_voltage'),
        "dcCurrent": record.get('dc_current'),
        "dcPower": record.get('dc_power'),
        "dcShuntVoltage": record.get('dc_shunt_voltage'),
        # Basement temperature (DS18B20)
        "basementF": record.get('basement_f'),
        "basementC": record.get('basement_c'),
        # External weather data
        "avgStrikeDistance": record.get('avg_strike_distance'),
        "dailyAccumulation": record.get('daily_accumulation'),
        "extF": record.get('Ext_F'),
        "extHumidity": record.get('Ext_humidity'),
        "illuminance": record.get('illuminance'),
        "inHg": record.get('inHg'),
        "rain": record.get('rain'),
        "solarRadiation": record.get('solar_radiation'),
        "strikeCount": record.get('strike_count'),
        "uv": record.get('uv'),
        "windAvg": record.get('wind_avg'),
        "windDirection": record.get('wind_direction'),
        "windGust": record.get('wind_gust'),
        # Inverter data
        "inverterAacOut": record.get('InverterAACOut'),
        "inverterFault": record.get('InverterFault'),
        "inverterMode": record.get('InverterMode'),
        "inverterOn": record.get('InverterOn'),
        "inverterVacOut": record.get('InverterVACOut'),
    }

    # Remove None values to keep payload clean
    return {k: v for k, v in payload.items() if v is not None}


# Columns of the Cloudflare D1 `measurements` table, in the order bound to
# the INSERT statement's positional (?) parameters. Must match the D1 schema.
D1_MEASUREMENT_COLUMNS = [
    "date",
    "ampHours",
    "avgStrikeDistance",
    "batteryState",
    "chargeState",
    "classicState",
    "dailyAccumulation",
    "dispavgVbatt",
    "dispavgVpv",
    "extF",
    "extHumidity",
    "humidity",
    "ibattDisplay",
    "illuminance",
    "inHg",
    "intF",
    "inverterAacOut",
    "inverterFault",
    "inverterMode",
    "inverterOn",
    "inverterVacOut",
    "kwhours",
    "niteMinutesNoPwr",
    "pvInputCurrent",
    "rain",
    "solarRadiation",
    "strikeCount",
    "uv",
    "vocLastMeasured",
    "watts",
    "windAvg",
    "windDirection",
    "windGust",
    "basementC",
    "basementF",
    "dcShuntVoltage",
    "dcPower",
    "dcBusVoltage",
    "dcCurrent",
]


def insert_measurements_to_d1(
    measurements: List[Dict],
    account_id: str,
    database_id: str,
    api_token: str,
    timeout: int = 30
) -> bool:
    """
    Insert measurement rows directly into Cloudflare D1 via the D1 HTTP API,
    bypassing any intermediate Worker/REST API.

    All rows are sent as a single batch, which D1 executes atomically.

    Args:
        measurements: List of rows in D1 format (see convert_measurement_to_d1_row)
        account_id: Cloudflare account ID
        database_id: D1 database UUID
        api_token: Cloudflare API token scoped with D1 edit permission
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    if not measurements:
        return True

    columns_sql = ", ".join(D1_MEASUREMENT_COLUMNS)
    placeholders = ", ".join(["?"] * len(D1_MEASUREMENT_COLUMNS))
    insert_sql = f"INSERT INTO measurements ({columns_sql}) VALUES ({placeholders})"

    batch = [
        {
            "sql": insert_sql,
            "params": [row.get(col) for col in D1_MEASUREMENT_COLUMNS]
        }
        for row in measurements
    ]

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json={"batch": batch}, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        logging.exception("Error connecting to Cloudflare D1 API")
        return False

    try:
        result = response.json()
    except ValueError:
        logging.exception("Error parsing Cloudflare D1 API response")
        return False

    if not result.get("success"):
        logging.error("Cloudflare D1 API returned errors: %s", result.get("errors"))
        return False

    rows_written = sum(
        statement_result.get("meta", {}).get("rows_written", 0)
        for statement_result in result.get("result", [])
    )
    logging.info(
        "Successfully inserted %d measurement(s) into D1 (%d rows written)",
        len(measurements),
        rows_written,
    )
    return True


def sync_unsynced_records(config: configparser.ConfigParser, batch_size: int = 10) -> tuple:
    """
    Sync all unsynced records to the remote API.

    This function will attempt to sync all unsynced records in batches.
    It stops on the first failure to avoid overwhelming the API or network.

    Args:
        config: Configuration object with database and API credentials
        batch_size: Number of records to process per batch

    Returns:
        Tuple of (total_synced, total_failed)
    """
    try:
        # Get Cloudflare D1 credentials from config file
        account_id = config.get('CloudflareD1', 'account_id')
        database_id = config.get('CloudflareD1', 'database_id')
        api_token = config.get('CloudflareD1', 'api_token')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logging.warning(
            "CloudflareD1 section not configured, skipping remote sync"
        )
        return (0, 0)

    total_synced = 0
    total_failed = 0

    # Process all unsynced records in batches
    while True:
        # Fetch unsynced measurements
        records = get_unsynced_measurements(config, batch_size)

        if not records:
            logging.info("No unsynced records to sync")
            break

        logging.info("Found %d unsynced records to sync", len(records))

        # Collect record dates and convert to D1 row format
        record_dates = []
        d1_rows = []

        for record in records:
            record_date = record.get('Date')
            if not record_date:
                logging.warning("Skipping record without Date")
                continue

            d1_rows.append(convert_measurement_to_d1_row(record))
            record_dates.append(record_date)

        if not d1_rows:
            logging.warning("No valid records to sync")
            break

        # Insert directly into D1
        logging.info("Inserting %d measurements into Cloudflare D1", len(d1_rows))
        if insert_measurements_to_d1(d1_rows, account_id, database_id, api_token):
            # Mark all records as synced
            success_count = 0
            fail_count = 0

            for record_date in record_dates:
                if mark_as_synced(config, record_date):
                    success_count += 1
                else:
                    fail_count += 1

            total_synced += success_count
            total_failed += fail_count

            logging.info(
                "Batch sync complete: %d successful, %d failed",
                success_count,
                fail_count
            )

            # If we had failures marking records, stop
            if fail_count > 0:
                break
        else:
            # D1 insert failed, stop trying
            logging.error("Failed to insert into D1, stopping sync")
            total_failed += len(record_dates)
            break

    if total_synced > 0 or total_failed > 0:
        logging.info(
            "Remote sync complete: %d total synced, %d total failed",
            total_synced,
            total_failed
        )

    return (total_synced, total_failed)
