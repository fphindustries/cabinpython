from influxdb import InfluxDBClient
import configparser

config = configparser.ConfigParser()
config.read('influx.ini')
client = InfluxDBClient(config['influxdb']['host'], config['influxdb']['port'], config['influxdb']['user'], config['influxdb']['password'], config['influxdb']['database'])


rows = list(client.query('select * from sensors where time > now() - 1h group by * order by desc limit 1;').get_points())
row = rows[0]
print(row)
dispavgVbatt = row["dispavgVbatt"]
dispavgVpv = row["dispavgVpv"]
batteryState = row["batteryState"]

print(dispavgVpv)

#result = client.query('select * from solar where time > now() - 1h group by * order by desc limit 1;')
#print("Result: {0}".format(result))

#print("Amp Hours: {0}".format(result.get_points('AmpHours')[0]))

#for table in result:
#data = list(result.get_points())
#print(data)
#print(data[0]["dispavgVpv"])
#table = next(result)
#print(table)
#print(table[0]["dispavgVpv"])
    #for record in table.records:
        #print(record)
        #print(str(record["_time"]) + " - " + record["location"] + ": " + str(record["_value"]))