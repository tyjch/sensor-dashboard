import "math"

roundFloat = (value, places) => {
  multiplier = math.pow10(n: places)
  return math.round(x: value * multiplier) / multiplier 
}

stateLimits = from(bucket: "thermometer")
  |> range(start: 0, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "Threshold")
  |> filter(fn: (r) => r["_field"] == "limit")
  |> last()

getStateLimit = (state_name) => {
  limitValue = stateLimits
    |> filter(fn: (r) => r["state"] == state_name)
    |> findColumn(fn: (key) => true, column: "_value")
  
  return if length(arr: limitValue) > 0 then
    limitValue[0]
  else
    999999.0
}

limitDisconnected = getStateLimit(state_name: "disconnected")
limitCold         = getStateLimit(state_name: "cold")
limitCool         = getStateLimit(state_name: "cool")
limitAverage      = getStateLimit(state_name: "average")
limitWarm         = getStateLimit(state_name: "warm")
limitHot          = getStateLimit(state_name: "hot")

limitMap = {
  disconnected : limitDisconnected,
  cold         : limitCold,
  cool         : limitCool,
  average      : limitAverage,
  warm         : limitWarm,
  hot          : limitHot
}

getState = (t) => {
  state = if t <= limitDisconnected then "disconnected"
  else if t <= limitCold then "cold"
  else if t <= limitCool then "cool"
  else if t <= limitAverage then "average"
  else if t <= limitWarm then "warm"
  else "hot"
  
  return state
}

bias = from(bucket: "thermometer")
  |> range(start: -1h, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "DS18B20")
  |> filter(fn: (r) => r["_field"] == "bias")
  |> keep(columns: ["_time", "_value", "sensor_id", "unit"])
  |> rename(columns: {_value: "bias_value"})
    
temperature = from(bucket: "thermometer")
  |> range(start: -1h, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "DS18B20")
  |> filter(fn: (r) => r["_field"] == "temperature")
  |> keep(columns: ["_time", "_value", "sensor_id", "unit"])
  |> rename(columns: {_value: "temperature_value"})

temperatureBiased = join(
  tables : {bias: bias, temperature: temperature},
  on     : ["_time", "sensor_id", "unit"]
)
  |> map(fn: (r) => ({
  _time     : r._time,
  _start    : r._start,
  _stop     : r._stop,
  _value    : roundFloat(value: r.temperature_value + r.bias_value, places:1),
  temp      : r.temperature_value,
  bias      : r.bias_value,
  sensor_id : r.sensor_id,
  unit      : r.unit
  }))
  |> sort(columns: ["_time"], desc: false)
  
temperatureBiasedWithState = temperatureBiased
  |> map(fn: (r) => ({
    _time     : r._time,
    _start    : r._start,
    _stop     : r._stop,
    _value    : r._value,
    temp      : r.temp,
    bias      : r.bias,
    sensor_id : r.sensor_id,
    unit      : r.unit,
    state     : getState(t: r._value)
  }))
  |> keep(columns: ["_time", "_value", "state"])

duration = 1s
temperatureBiasedWithState
  |> stateTracking(
      fn: (r) => r.state == "disconnected",
      durationColumn : "disconnected_duration", 
      countColumn    : "disconnected_count",
      durationUnit   : duration
    )
  |> stateTracking(
      fn: (r) => r.state == "cold",
      durationColumn : "cold_duration", 
      countColumn    : "cold_count",
      durationUnit   : duration
    )
  |> stateTracking(
      fn: (r) => r.state == "cool",
      durationColumn : "cool_duration", 
      countColumn    : "cool_count",
      durationUnit   : duration
    )
  |> stateTracking(
      fn: (r) => r.state == "average",
      durationColumn : "average_duration", 
      countColumn    : "average_count",
      durationUnit   : duration
    )
  |> stateTracking(
      fn: (r) => r.state == "warm",
      durationColumn : "warm_duration", 
      countColumn    : "warm_count",
      durationUnit   : duration
    )
  |> stateTracking(
      fn: (r) => r.state == "hot",
      durationColumn : "hot_duration", 
      countColumn    : "hot_count",
      durationUnit   : duration
    )
  |> group(columns: ["state"])
  |> last()
  |> map(fn: (r) => ({
    r with
    count: if r.state == "disconnected" then r.disconnected_count
           else if r.state == "cold" then r.cold_count
           else if r.state == "cool" then r.cool_count
           else if r.state == "average" then r.average_count
           else if r.state == "warm" then r.warm_count
           else if r.state == "hot" then r.hot_count
           else -1,
    duration: if r.state == "disconnected" then r.disconnected_duration
              else if r.state == "cold" then r.cold_duration
              else if r.state == "cool" then r.cool_duration
              else if r.state == "average" then r.average_duration
              else if r.state == "warm" then r.warm_duration
              else if r.state == "hot" then r.hot_duration
              else -1
  }))
  |> drop(columns: [
      "disconnected_count",
      "disconnected_duration", 
      "cold_count",
      "cold_duration",
      "cool_count",
      "cool_duration",
      "average_count",
      "average_duration",
      "warm_count",
      "warm_duration",
      "hot_count",
      "hot_duration"
  ])
  |> sort(columns: ["_value"])
  |> yield(name: "state_tracking")