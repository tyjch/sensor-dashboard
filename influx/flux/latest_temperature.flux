bias = from(bucket: "thermometer")
  |> range(start: 0, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "DS18B20")
  |> filter(fn: (r) => r["_field"] == "bias")
  |> sort(columns: ["_time"])
  |> last()
  |> keep(columns: ["_time", "_value", "sensor_id", "unit"])
  |> rename(columns: {_value: "bias_value"})

temperature = from(bucket: "thermometer")
  |> range(start: 0, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "DS18B20")
  |> filter(fn: (r) => r["_field"] == "temperature")
  |> sort(columns: ["_time"])
  |> last()
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
  |> yield(name: "temperatureBiased")