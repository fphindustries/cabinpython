#!/opt/cabinpython/env/bin/python3

import datetime
import configparser
import mysql.connector
import board
import os
import logging
import adafruit_sht31d
import minimalmodbus
import argparse
import requests
import magnum
import ssl
import smtplib
import time
import json
from pathlib import Path
from email.message import EmailMessage
from magnum.magnum import Magnum

ALERT_STATE_FILE = Path('/opt/cabinpython/last_battery_alert.json')

def _read_alert_state():
    if ALERT_STATE_FILE.exists():
        try:
            return json.loads(ALERT_STATE_FILE.read_text())
        except Exception:
            logging.exception("Error in _read_alert_state")

            return {}
    return {}

def _write_alert_state(state: dict):
    try:
        ALERT_STATE_FILE.write_text(json.dumps(state))
    except Exception:
        logging.exception("Failed to write alert state file")

def send_email(
    smtp_server: str, smtp_port: int, smtp_user: str, smtp_pass: str,
    from_addr: str, to_addr: str, subject: str, body: str
) -> bool:

    # Parse comma-separated addresses
    recipients = [addr.strip() for addr in to_addr.split(",") if addr.strip()]

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)   # Header only
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)

            # IMPORTANT: explicitly pass recipient list
            server.send_message(msg, from_addr=from_addr, to_addrs=recipients)

        logging.info("Email sent to %s", recipients)
        return True

    except Exception:
        logging.exception("Failed to send email to %s", recipients)
        return False

def notify_if_low_battery(config, measurements):

    try:
        # Check if Notify section exists
        if not config.has_section('Notify'):
            logging.debug("Notify section not configured, skipping battery alerts")
            return

        low_thr = float(config.get('Notify','battery_low_threshold', fallback='12.3'))
        recover_thr = float(config.get('Notify','battery_recovery_threshold', fallback='12.8'))
        cooldown_min = int(config.get('Notify','alert_cooldown_minutes', fallback='30'))
        to_addr = config.get('Notify','to_addr', fallback=None)
        from_addr = config.get('Notify','from_addr', fallback=None)
        smtp_server = config.get('Notify','smtp_server', fallback=None)
        smtp_port = config.getint('Notify','smtp_port', fallback=465)
        smtp_user = config.get('Notify','smtp_user', fallback=None)
        smtp_pass = os.getenv('SMTP_PASS') or config.get('Notify','smtp_pass', fallback=None)

        # Validate required fields
        if not all([to_addr, from_addr, smtp_server, smtp_user, smtp_pass]):
            logging.warning("Notify section incomplete, skipping battery alerts")
            return

        # choose which voltage measurement to use (adjust key if needed)
        volts = measurements.get('dispavgVbatt')
        if volts is None:
            return

        state = _read_alert_state()
        last_alert_ts = state.get('last_alert_ts')  # epoch seconds
        alerted = state.get('alerted', False)

        now_ts = int(time.time())
        should_send = False

        if not alerted and volts < low_thr:
            should_send = True
        elif alerted:
            # only clear alert when it recovers above recovery threshold
            if volts >= recover_thr:
                # clear alert state so future lows can alert again
                subject = f"Battery alert cleared: {volts:.2f} V"
                body = f"Battery voltage is {volts:.2f} V at {datetime.datetime.now().isoformat()}.\n\nDetails: {measurements}"
                sent = send_email(smtp_server, smtp_port, smtp_user, smtp_pass, from_addr, to_addr, subject, body)                
                state['alerted'] = False
                state['last_alert_ts'] = None
                _write_alert_state(state)
                logging.info("Battery recovered to %s, cleared alert state", volts)
                return
            # else still alerted: but consider cooldown - allow re-send if cooldown passed (optional)
            if last_alert_ts and (now_ts - last_alert_ts) >= (cooldown_min * 60):
                should_send = True

        if should_send:
            subject = f"Battery alert: {volts:.2f} V"
            body = f"Battery voltage is {volts:.2f} V at {datetime.datetime.now().isoformat()}.\n\nDetails: {measurements}"
            sent = send_email(smtp_server, smtp_port, smtp_user, smtp_pass, from_addr, to_addr, subject, body)
            if sent:
                state['alerted'] = True
                state['last_alert_ts'] = now_ts
                _write_alert_state(state)
    except Exception:
        logging.exception("Error in notify_if_low_battery")

def get_sht31():
    """
    Get the temperature and humidity from the SHT31 sensor.

    Returns:
        dict: A dictionary containing the temperature in Celsius, temperature in Fahrenheit, and humidity.
    """
    # Get the temperature and humidity from the SHT31 sensor
    try:
        i2c = board.I2C()  # uses board.SCL and board.SDA
        sensor = adafruit_sht31d.SHT31D(i2c)
        int_c = sensor.temperature
        humidity = sensor.relative_humidity
        # Convert int_c from Celsius to Fahrenheit
        int_f = (int_c * 9/5) + 32
        return {'int_c': int_c, 'int_f': int_f, 'humidity': humidity}
    except Exception:
        logging.exception("Error reading from SHT31 sensor")
        return {'int_c': None, 'int_f': None, 'humidity': None}

def get_inverter_data(config):
    """
    Get the inverter data via serial port.

    Args:
        config (ConfigParser): The configuration object containing the instrument port.

    Returns:
        dict: A dictionary containing the inverter data.
    """
    try:
        inverter_port = config.get('Inverter', 'port')
        magnumReader = Magnum(device=inverter_port)
        devices = magnumReader.getDevices()  # test read to see if all's good
        inverter = next(device for device in devices if device['device'] =='INVERTER')
        data = {
            'InverterOn': inverter['data']['invled'],
            'InverterMode': inverter['data']['mode'],
            'InverterFault': inverter['data']['fault'],
            'InverterVACOut': inverter['data']['VACout'],
            'InverterAACOut': inverter['data']['adc'],
            'Invertervdc': inverter['data']['vdc']
        }
        return data
    except Exception:
        logging.exception("Error getting inverter data")
        return {
            'InverterOn': None,
            'InverterMode': None,
            'InverterFault': None,
            'InverterVACOut': None,
            'InverterAACOut': None,
            'Invertervdc': None            
        }
     
def get_solar_data(config):
    """
    Get the solar data from the instrument.

    Args:
        config (ConfigParser): The configuration object containing the instrument port.

    Returns:
        dict: A dictionary containing the solar data.
    """
    try:
        # Get the instrument port from the configuration file
        solar_port = config.get('Solar', 'port')

        # Create the instrument object
        instrument = minimalmodbus.Instrument(solar_port, 10)

        registers = instrument.read_registers(4114, 29)
        instrument.serial.close()
        data = {
            'dispavgVbatt': registers[0]/10.0,
            'dispavgVpv': registers[1]/10.0,
            'IbattDisplay': registers[2]/10.0,
            'kWHours': registers[3]/10.0,
            'watts': registers[4],
            'chargeState': registers[5],
            'batteryState': (registers[5] & 0xFF00) >> 8,
            'classicState': registers[5] & 0xFF,
            'PvInputCurrent': registers[6]/10.0,
            'VocLastMeasured': registers[7]/10.0,
            'HighestVinputLog': registers[8]/10.0,
            'AmpHours': registers[10],
            'LifeTimekWHours': registers[11],
            'LifetimeAmpHours': registers[12],
            'BATTtemperature': registers[17],
            'NiteMinutesNoPwr': registers[20],
            'FloatTime': registers[23],
            'AbsorbTime': registers[24],
            'EqualizeTime': registers[28]
        }

        return data

    except Exception:
        logging.exception("Error getting solar data")
        return {
            'dispavgVbatt': None,
            'dispavgVpv': None,
            'IbattDisplay': None,
            'kWHours': None,
            'watts': None,
            'chargeState': None,
            'batteryState': None,
            'classicState': None,
            'PvInputCurrent': None,
            'VocLastMeasured': None,
            'HighestVinputLog': None,
            'AmpHours': None,
            'LifeTimekWHours': None,
            'LifetimeAmpHours': None,
            'BATTtemperature': None,
            'NiteMinutesNoPwr': None,
            'FloatTime': None,
            'AbsorbTime': None,
            'EqualizeTime': None            
        }

def insert_measurement_to_database(current_time, config, measurements):
    """
    Insert the SHT31 measurements into the database.

    Args:
        current_time (datetime): The current time.
        config (ConfigParser): The configuration object containing the database username and password.
        measurements (dict): A dictionary containing the measurements.

    Returns:
        None
    """
    # Get the database username and password from the configuration file
    try:
        username = config.get('Database', 'username')
        password = config.get('Database', 'password')
        database = config.get('Database', 'database')

        # Connect to the database
        mydb = mysql.connector.connect(
            host="localhost",
            database=database,
            user=username,
            password=password
        )

        # Insert the measurements into the measurements table
        cursor = mydb.cursor()
        sql = ("INSERT INTO measurements (Date, AbsorbTime, AmpHours, EqualizeTime, FloatTime, "
               "HighestVinputLog, IbattDisplay, NiteMinutesNoPwr, PvInputCurrent, VocLastMeasured, "
               "BatteryState, ChargeState, ClassicState, DispavgVbatt, DispavgVpv, kWHours, Watts, "
               "int_c, int_f, humidity, Ext_F, inHg, wind_avg, wind_gust, wind_direction, illuminance, "
               "uv, solar_radiation, rain, avg_strike_distance, strike_count, weather_battery, "
               "daily_accumulation, Ext_humidity, InverterOn, InverterMode, InverterFault, InverterVACOut, InverterAACOut) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

        # Use .get() to avoid KeyError if some sensor data is missing
        values = (
            current_time,
            measurements.get('AbsorbTime'),
            measurements.get('AmpHours'),
            measurements.get('EqualizeTime'),
            measurements.get('FloatTime'),
            measurements.get('HighestVinputLog'),
            measurements.get('IbattDisplay'),
            measurements.get('NiteMinutesNoPwr'),
            measurements.get('PvInputCurrent'),
            measurements.get('VocLastMeasured'),
            measurements.get('batteryState'),
            measurements.get('chargeState'),
            measurements.get('classicState'),
            measurements.get('dispavgVbatt'),
            measurements.get('dispavgVpv'),
            measurements.get('kWHours'),
            measurements.get('watts'),
            measurements.get('int_c'),
            measurements.get('int_f'),
            measurements.get('humidity'),
            measurements.get('ext_temp'),
            measurements.get('pressure'),
            measurements.get('wind_avg'),
            measurements.get('wind_gust'),
            measurements.get('wind_direction'),
            measurements.get('illuminance'),
            measurements.get('uv'),
            measurements.get('solar_radiation'),
            measurements.get('rain'),
            measurements.get('avg_strike_distance'),
            measurements.get('strike_count'),
            measurements.get('weather_battery'),
            measurements.get('daily_accumulation'),
            measurements.get('ext_humidity'),
            measurements.get('InverterOn'),
            measurements.get('InverterMode'),
            measurements.get('InverterFault'),
            measurements.get('InverterVACOut'),
            measurements.get('InverterAACOut')
        )
        cursor.execute(sql, values)
        mydb.commit()
        logging.debug("Successfully inserted measurement record for %s", current_time)

    except mysql.connector.Error as e:
        logging.error("Database error inserting measurements: %s", str(e))
        logging.debug("Failed values: %s", values)
    except Exception:
        logging.exception("Unexpected error inserting measurements into the database")
    finally:
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
        except Exception:
            logging.exception("Error closing cursor")
        try:
            if 'mydb' in locals() and mydb:
                mydb.close()
        except Exception:
            logging.exception("Error closing database connection")


def call_json_api(url):
    """
    Call a JSON API and return the response.

    Args:
        url (str): The URL of the JSON API.

    Returns:
        dict: The JSON response from the API.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        logging.exception("Error calling JSON API %s", url)
        return None

def mps_to_mph(mps):
    """
    Convert meters per second to miles per hour.

    Args:
        mps (float): Speed in meters per second.

    Returns:
        float: Speed in miles per hour.
    """
    mph = mps * 2.23694
    return mph

def mb_to_inhg(mb):
    """
    Convert millibar to inches of mercury.

    Args:
        mb (float): Pressure in millibar.

    Returns:
        float: Pressure in inches of mercury.
    """
    inhg = mb * 0.02953
    return inhg

def celsius_to_fahrenheit(celsius):
    """
    Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius (float): Temperature in Celsius.

    Returns:
        float: Temperature in Fahrenheit.
    """
    fahrenheit = (celsius * 9/5) + 32
    return fahrenheit

def mm_to_inches(mm):
    """
    Convert millimeters to inches.

    Args:
        mm (float): Length in millimeters.

    Returns:
        float: Length in inches.
    """
    inches = mm / 25.4
    return inches

def km_to_miles(km):
    """
    Convert kilometers to miles.

    Args:
        km (float): Distance in kilometers.

    Returns:
        float: Distance in miles.
    """
    miles = km * 0.621371
    return miles

def get_weather(config):
    """
    Get the weather data from the OpenWeatherMap API.

    Args:
        config (ConfigParser): The configuration object containing the API key.

    Returns:
        dict: A dictionary containing the weather data.
    """
    try:
        device = config.get('Weather', 'device')
        token = config.get('Weather', 'token', fallback=os.getenv('WEATHER_TOKEN'))

        if not token:
            raise RuntimeError('Weather token not set in config or WEATHER_TOKEN')

        weather = call_json_api(f'https://swd.weatherflow.com/swd/rest/observations/device/{device}?token={token}')
        if not weather or 'obs' not in weather or not weather['obs']:
            raise RuntimeError('Invalid weather response')

        obs = weather['obs'][0]
        conditions = {
            'wind_avg' : mps_to_mph(obs[2]),
            'wind_gust' : mps_to_mph(obs[3]),
            'wind_direction' : obs[4],
            'pressure' : mb_to_inhg(obs[6]),
            'ext_temp' : celsius_to_fahrenheit(obs[7]),
            'ext_humidity' : obs[8],
            'illuminance': obs[9],
            'uv' : obs[10],
            'solar_radiation': obs[11],
            'rain': mm_to_inches(obs[12]),
            'avg_strike_distance': km_to_miles(obs[14]),
            'strike_count' : obs[15],
            'weather_battery': obs[16],
            'daily_accumulation': mm_to_inches(obs[18])
        }

        return conditions

    except Exception as e:
        logging.exception("Error getting weather data")
        return {
            'wind_avg' : None,
            'wind_gust' : None,
            'wind_direction' : None,
            'pressure' : None,
            'ext_temp' : None,
            'ext_humidity' : None,
            'illuminance': None,
            'uv' : None,
            'solar_radiation': None,
            'rain': None,
            'avg_strike_distance': None,
            'strike_count' : None,
            'weather_battery': None,
            'daily_accumulation': None
        }
        
def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to the configuration file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose debug logging')
    args = parser.parse_args(argv)

    # Set logging level based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s %(levelname)s %(message)s')

    config_file = args.config if args and args.config else 'config.ini'
    config = configparser.ConfigParser()
    config.read(config_file)

    current_time = datetime.datetime.now().replace(second=0, microsecond=0)
    logging.info("Starting measurement capture at %s", current_time)

    # Collect sensor data
    logging.debug("Reading SHT31 sensor...")
    sht31 = get_sht31()

    logging.debug("Reading solar charge controller...")
    solar_data = get_solar_data(config)

    logging.debug("Reading weather data...")
    conditions = get_weather(config)

    logging.debug("Reading inverter data...")
    inverter_data = get_inverter_data(config)

    # Merge all sensor data into a single dictionary
    all_data = {**sht31, **solar_data, **conditions, **inverter_data}

    # Log key metrics for monitoring
    logging.info("Battery: %.2fV, Solar: %dW, Indoor: %.1fF/%.0f%%, Outdoor: %.1fF",
                 all_data.get('dispavgVbatt', 0.0) or 0.0,
                 all_data.get('watts', 0) or 0,
                 all_data.get('int_f', 0.0) or 0.0,
                 all_data.get('humidity', 0.0) or 0.0,
                 all_data.get('ext_temp', 0.0) or 0.0)

    # Insert the measurements into the database
    insert_measurement_to_database(current_time, config, all_data)

    # Check for low battery and send alerts
    notify_if_low_battery(config, all_data)

    # Attempt to sync all unsynced records to remote API
    # This stops on first failure since the script runs every 5 minutes
    try:
        from sync_common import sync_unsynced_records
        total_synced, total_failed = sync_unsynced_records(config, batch_size=10)
        if total_synced > 0:
            logging.info("Synced %d records to remote API", total_synced)
        if total_failed > 0:
            logging.warning("Failed to sync %d records to remote API", total_failed)
    except Exception:
        logging.exception("Error syncing to remote API (will retry on next run)")

    logging.info("Measurement capture completed")


if __name__ == "__main__":
    main()
