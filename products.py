from Forecast import getForecast
from alert_summary import getAlertSummary
from hazardous_weather_outlook import getHazardousWeatherOutlook
from tropical_weather_outlook import getTropicalWeatherOutlook
from current_time import getCurrentTime
from area_observations import getObservations
from marine_forecast import getMarineForecast
from regional_summary import getRegionalSummary
from StationID import getStationID
from RWT import getRWT

PRODUCT_GENERATORS = (
    getAlertSummary,
    getForecast,
    getMarineForecast,
    getRegionalSummary,
    getObservations,
    getHazardousWeatherOutlook,
    getTropicalWeatherOutlook,
    getCurrentTime,
)
