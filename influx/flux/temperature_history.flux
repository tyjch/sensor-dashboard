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

temperatureBiased = join(
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
  |> aggregateWindow(every: 5m, fn: mean, column: "temperature_biased")
  |> yield(name: "temperatureBiased")