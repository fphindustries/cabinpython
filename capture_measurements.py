import datetime
import configparser
import mysql.connector
import board
import adafruit_sht31d
import minimalmodbus
import argparse

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
        sql = "INSERT INTO measurements (Date, AbsorbTime, AmpHours, EqualizeTime, FloatTime, HighestVinputLog, IbattDisplay, NiteMinutesNoPwr, PvInputCurrent, VocLastMeasured, BatteryState, ChargeState, ClassicState, DispavgVbatt, kWHours, Watts, int_c, int_f, humidity) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
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
            measurements['kWHours'],
            measurements['watts'],
            measurements['int_c'],
            measurements['int_f'],
            measurements['humidity']
        )
        cursor.execute(sql, values)
        mydb.commit()
        cursor.close()

    except Exception as e:
        print("Error inserting measurements into the database:", str(e))


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

    # Merge sht31 and solar_data into a single dictionary
    all_data = {**sht31, **solar_data}

    # Insert the SHT31 measurements into the database
    insert_measurement_to_database(current_time, config, all_data)