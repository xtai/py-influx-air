"""CLI Entry point"""
import argparse
import time

from influxdb import InfluxDBClient
from datetime import datetime, timezone

from . import BME680, SDS011

influx_client = None
influx_db = None

def main():
    """Invoke the parser"""

    parser = argparse.ArgumentParser(description='Parse sds011 and bme680 sensor data to an InfluxDB instance.')
    parser.add_argument('-p', '--port', help='SDS011 serial port', default='/dev/ttyUSB0')
    parser.add_argument('-i', '--influx', help='InfluxDB host', default='localhost')
    parser.add_argument('-d', '--database', help='InfluxDB database')
    parser.add_argument('-s', '--sds011_measurement', help='InfluxDB measurement for sds011 data')
    parser.add_argument('-b', '--bme680_measurement', help='InfluxDB measurement for bme680 data')
    parser.add_argument('-l', '--location', help='InfluxDB tag for location')
    parser.add_argument('-g', '--geohash', help='InfluxDB tag for geohash')
    args = parser.parse_args()

    global influx_db, influx_client
    influx_client = InfluxDBClient(host=args.influx, port=8086)
    influx_db = args.database

    sds011_measurement = args.sds011_measurement
    bme680_measurement = args.bme680_measurement

    geohash = args.geohash
    location = args.location

    # Connect to sds011 via port, default: /dev/ttyUSB0
    sensor011 = SDS011.SDS011(args.port, use_query_mode=True)

    # Connect to bme680 via I2C
    try:
      sensor680 = BME680.BME680(BME680.I2C_ADDR_PRIMARY)
    except IOError:
      sensor680 = BME680.BME680(BME680.I2C_ADDR_SECONDARY)
    sensor680.set_humidity_oversample(BME680.OS_2X)
    sensor680.set_pressure_oversample(BME680.OS_4X)
    sensor680.set_temperature_oversample(BME680.OS_8X)
    sensor680.set_filter(BME680.FILTER_SIZE_3)

    # Designed to roughly model a 20 minutes cycle
    warmup = 22 # 22 seconds to warm-up for sds011 and bme680

    # 5 min bme680 & 20 min sds011 cycle
    interval = 300 # 300 sec/5 min - bme680 interval
    cycle = 4 # 4:1 bme680-sds011 result ratio

    # 30 sec bme680 + 15 min sds011 cycle
    # interval = 30 # 30 sec/0.5 min - bme680 interval
    # cycle = 30 # 30:1 bme680-sds011 result ratio

    print("Starting sds011 and bme680...")

    while True:
        # 0 sec - warm-up sds011
        sensor011.sleep(sleep=False)
        
        # 0 sec - warm-up bme680, while waiting for sds011 to wake up
        for i in range(warmup):
            sensor680.get_sensor_data()
            time.sleep(1)

        # warmup secs - read from sds011
        results = []
        ts = datetime.now(timezone.utc).astimezone().isoformat()
        result = sensor011.query()
        if result is not None:
            pm25, pm100 = result
            measurement = measurement_from_sds011(ts, sds011_measurement, pm25, pm100, geohash, location)
            results.append(measurement)
            print("SDS011: PM2.5 {}; PM10 {}".format(pm25, pm100))
        else:
            print("No response from SDS011 sensor")
        sensor011.sleep()

        # warmup secs - read from bme680
        if sensor680.get_sensor_data():
            temp, pres, humi = sensor680.data.temperature, sensor680.data.pressure, sensor680.data.humidity
            measurement = measurement_from_bme680(ts, bme680_measurement, temp, pres, humi, geohash, location)
            results.append(measurement)
            print("BME680: {0:.2f} C; {1:.2f} hPa; {2:.3f} %RH".format(temp, pres, humi))
        else:
            print("No response from BME680 sensor")
        
        # warmup secs - Write sds010 and bme680 results
        influx_client.write_points(results, database=influx_db)
        
        # warmup secs - wait for the bme680-only cycles
        time.sleep(interval - warmup)

        # interval secs - bme680-only cycles
        for i in range(cycle - 1):
            # warm-up bme680
            for w in range(warmup):
                sensor680.get_sensor_data()
                time.sleep(1)

            # read from bme680
            results = []
            ts = datetime.now(timezone.utc).astimezone().isoformat()
            if sensor680.get_sensor_data():
                temp, pres, humi = sensor680.data.temperature, sensor680.data.pressure, sensor680.data.humidity
                measurement = measurement_from_bme680(ts, bme680_measurement, temp, pres, humi, geohash, location)
                results.append(measurement)
                print("BME680: {0:.2f} C; {1:.2f} hPa; {2:.3f} %RH".format(temp, pres, humi))
            else:
                print("No response from BME680 sensor")
            influx_client.write_points(results, database=influx_db)

            # wait for the next bme680-only cycle
            time.sleep(interval - warmup)

def measurement_from_sds011(timestamp, measurement, pm25, pm100, geohash, location):
    """Turn the SDS011 object into a set of influx-db compatible measurement object"""

    return {
        "measurement": str(measurement),
        "tags": {
            "sensor": "sds011",
            "location": str(location),
            "geohash": str(geohash),
        },
        "time": timestamp,
        "fields": {
            "pm25": float(pm25),
            "pm100": float(pm100)
        }
    }

def measurement_from_bme680(timestamp, measurement, temperature, pressure, humidity, geohash, location):
    """Turn the BME680 object into a set of influx-db compatible measurement object"""

    return {
        "measurement": str(measurement),
        "tags": {
            "sensor": "bme680",
            "location": str(location),
            "geohash": str(geohash),
        },
        "time": timestamp,
        "fields": {
            "temperature": float(temperature),
            "pressure": float(pressure),
            "humidity": float(humidity)
        }
    }

if __name__ == "__main__":
    main()
