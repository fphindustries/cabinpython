import datetime
import configparser
import mysql.connector
import board
import adafruit_sht31d
import minimalmodbus
import argparse
import requests
import magnum
from magnum.magnum import Magnum

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
    except Exception as e:
        print("Error reading from SHT31 sensor:", str(e))
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
            'InverterAACOut': inverter['data']['AACout'],
            'Invertervdc': inverter['data']['vdc']
        }
        return data
    except Exception as e:
        print("Error getting inverter data:", str(e))
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

    except Exception as e:
        print("Error getting solar data:", str(e))
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

        # Insert the sht31 dictionary into the measurements table
        cursor = mydb.cursor()
        sql = "INSERT INTO measurements (Date, AbsorbTime, AmpHours, EqualizeTime, FloatTime, HighestVinputLog, IbattDisplay, NiteMinutesNoPwr, PvInputCurrent, VocLastMeasured, BatteryState, ChargeState, ClassicState, DispavgVbatt, DispavgVpv, kWHours, Watts, int_c, int_f, humidity, Ext_F, inHg, wind_avg, wind_gust, wind_direction, illuminance, uv, solar_radiation, rain, avg_strike_distance, strike_count, weather_battery, daily_accumulation, Ext_humidity, InverterOn, InverterMode, InverterFault, InverterVACOut, InverterAACOut) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (
            current_time,
            measurements['AbsorbTime'],
            measurements['AmpHours'],
            measurements['EqualizeTime'],
            measurements['FloatTime'],
            measurements['HighestVinputLog'],
            measurements['IbattDisplay'],
            measurements['NiteMinutesNoPwr'],
            measurements['PvInputCurrent'],
            measurements['VocLastMeasured'],
            measurements['batteryState'],
            measurements['chargeState'],
            measurements['classicState'],
            measurements['dispavgVbatt'],
            measurements['dispavgVpv'],
            measurements['kWHours'],
            measurements['watts'],
            measurements['int_c'],
            measurements['int_f'],
            measurements['humidity'],
            measurements['ext_temp'],
            measurements['pressure'],
            measurements['wind_avg'],
            measurements['wind_gust'],
            measurements['wind_direction'],
            measurements['illuminance'],
            measurements['uv'],
            measurements['solar_radiation'],
            measurements['rain'],
            measurements['avg_strike_distance'],
            measurements['strike_count'],
            measurements['weather_battery'],
            measurements['daily accumulation'],
            measurements['ext_humidity'],
            measurements['InverterOn'],
            measurements['InverterMode'],
            measurements['InverterFault'],
            measurements['InverterVACOut'],
            measurements['InverterAACOut']
        )
        cursor.execute(sql, values)
        mydb.commit()
        cursor.close()

    except Exception as e:
        print("Error inserting measurements into the database:", str(e))


def call_json_api(url):
    """
    Call a JSON API and return the response.

    Args:
        url (str): The URL of the JSON API.

    Returns:
        dict: The JSON response from the API.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error calling JSON API:", str(e))
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
        token = config.get('Weather', 'token')

        token = '5407c1ea-bc93-4960-98f8-488f3b227620'
        weather = call_json_api(f'https://swd.weatherflow.com/swd/rest/observations/device/{device}?token={token}')
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
            'daily accumulation': mm_to_inches(obs[18])
        }

        return conditions

    except Exception as e:
        print("Error getting weather data:", str(e))
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
            'daily accumulation': None
        }
        
if __name__ == "__main__":
    current_time = datetime.datetime.now().replace(second=0, microsecond=0)
    config = configparser.ConfigParser()
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to the configuration file')
    args = parser.parse_args()

    config_file = args.config if args.config else 'config.ini'
    config.read(config_file)

    sht31 = get_sht31()
    solar_data = get_solar_data(config)
    
    conditions = get_weather(config)

    inverter_data = get_inverter_data(config)

    # Merge sht31 and solar_data into a single dictionary
    all_data = {**sht31, **solar_data, **conditions, **inverter_data}
    #print(all_data)
    # Insert the SHT31 measurements into the database
    insert_measurement_to_database(current_time, config, all_data)
