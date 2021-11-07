from influxdb import InfluxDBClient
import configparser

config = configparser.ConfigParser()
config.read('influx.ini')
client = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'], config['influxdb']['user'], config['influxdb']['password'], config['influxdb']['database'])
result = client.query('select * from solar where time > now() - 1h group by * order by desc limit 1;')
print("Result: {0}".format(result))
print("Amp Hours: {0}".format(result.get_points('AmpHours')[0])
