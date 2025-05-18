import "timezone"
import "date"

// Set your timezone as a global option
option location = timezone.location(name: "America/Los_Angeles")

// Now today() will respect the timezone set above
todayStart = today()
todayEnd = date.add(d: 1d, to: todayStart)

bias = from(bucket: "thermometer")
  |> range(start: todayStart, stop: todayEnd)
  |> filter(fn: (r) => r["_measurement"] == "DS18B20")
  |> filter(fn: (r) => r["_field"] == "bias")
  |> keep(columns: ["_time", "_value", "sensor_id", "unit"])
  |> rename(columns: {_value: "bias_value"})

temperature = from(bucket: "thermometer")
  |> range(start: todayStart, stop: todayEnd)
  |> filter(fn: (r) => r["_measurement"] == "DS18B20")
  |> filter(fn: (r) => r["_field"] == "temperature")
  |> keep(columns: ["_time", "_value", "sensor_id", "unit"])
  |> rename(columns: {_value: "temperature_value"})

// Join and calculate all values
joined_data = join(
  tables : {bias: bias, temperature: temperature},
  on     : ["_time", "sensor_id", "unit"]
)
  |> map(fn: (r) => ({
    _time              : r._time,
    bias               : r.bias_value,
    temperature_raw    : r.temperature_value,
    temperature_biased : r.temperature_value + r.bias_value, 
    sensor_id          : r.sensor_id,
    unit               : r.unit
  }))

// Aggregate each column separately (likely faster than reduce)
bias_agg = joined_data
  |> aggregateWindow(every: 5m, fn: mean, column: "bias")
  |> keep(columns: ["_time", "bias"])

temperature_raw_agg = joined_data
  |> aggregateWindow(every: 5m, fn: mean, column: "temperature_raw")
  |> keep(columns: ["_time", "temperature_raw"])

temperature_biased_agg = joined_data
  |> aggregateWindow(every: 5m, fn: mean, column: "temperature_biased")
  |> keep(columns: ["_time", "temperature_biased"])

// Join with nested joins (InfluxDB only allows 2 parents per join)
first_join = join(
  tables: {
    bias: bias_agg,
    temp_raw: temperature_raw_agg
  },
  on: ["_time"]
)

// Second join to add the third column
temperatureBiased = join(
  tables: {
    combined: first_join,
    temp_biased: temperature_biased_agg
  },
  on: ["_time"]
)
  |> keep(columns: ["_time", "bias", "temperature_raw", "temperature_biased"])
  |> yield(name: "temperatureBiased")