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


def convert_measurement_to_api_format(record: Dict) -> Dict:
    """
    Convert a database record to the API's expected format based on OpenAPI spec.

    Args:
        record: Database record dictionary

    Returns:
        Dictionary in API format (flat structure with camelCase fields)
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
        # Indoor sensor data
        "intF": record.get('int_f'),
        "humidity": record.get('humidity'),
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


def send_to_api(
    measurements: List[Dict],
    api_url: str,
    client_id: str,
    client_secret: str,
    timeout: int = 30
) -> bool:
    """
    Send measurements to the Cloudflare-protected API.

    Args:
        measurements: List of measurement data in API format
        api_url: API endpoint URL
        client_id: Cloudflare Access Client ID
        client_secret: Cloudflare Access Client Secret
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    try:
        headers = {
            'CF-Access-Client-Id': client_id,
            'CF-Access-Client-Secret': client_secret,
            'Content-Type': 'application/json'
        }

        # Wrap measurements in records array as per OpenAPI spec
        payload = {
            'records': measurements
        }

        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=timeout
        )

        response.raise_for_status()
        result = response.json()
        logging.info(
            "Successfully sent to API: %s inserted out of %s total",
            result.get('inserted', 0),
            result.get('total', 0)
        )
        return True

    except requests.exceptions.RequestException:
        logging.exception("Error sending measurements to API")
        return False


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
        # Get Cloudflare credentials from config file
        client_id = config.get('CloudflareAccess', 'client_id')
        client_secret = config.get('CloudflareAccess', 'client_secret')
        api_url = config.get('CloudflareAccess', 'api_url',
                            fallback='https://cabinpi.com/api/sensors/ingest')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logging.warning(
            "CloudflareAccess section not configured, skipping remote sync"
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

        # Collect record dates and convert to API format
        record_dates = []
        api_measurements = []

        for record in records:
            record_date = record.get('Date')
            if not record_date:
                logging.warning("Skipping record without Date")
                continue

            api_payload = convert_measurement_to_api_format(record)
            api_measurements.append(api_payload)
            record_dates.append(record_date)

        if not api_measurements:
            logging.warning("No valid records to sync")
            break

        # Send to API
        logging.info("Sending %d measurements to remote API", len(api_measurements))
        if send_to_api(api_measurements, api_url, client_id, client_secret):
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
            # API call failed, stop trying
            logging.error("Failed to send to API, stopping sync")
            total_failed += len(record_dates)
            break

    if total_synced > 0 or total_failed > 0:
        logging.info(
            "Remote sync complete: %d total synced, %d total failed",
            total_synced,
            total_failed
        )

    return (total_synced, total_failed)
