# Clima Cast

NWS V3 API based weather Alexa skill

Using information provided by the National Weather Service, Clima Cast gives you the current conditions and the 7-day forecast for your area or any other United States city.

## Project Information

- **Documentation**: See [CHANGELOG.md](CHANGELOG.md) for project history and [docs/](docs/) for technical documentation
- **Source Code**: https://github.com/lllucius/climacast
- **License**: AGPL-3.0 (see [LICENSE](LICENSE))

## Features

### Weather Queries

    temperature or temp
    wind chill
    heat index
    dew point
    barometric pressure or pressure
    relative humidity or humidity
    precipitation, rain chance, snow chance, chance of rain or chance of snow
    wind

### Location Formats

When using a location, you may use either the city name and state or the zip code, like:

    Boulder, Colorado
    55118
    zip code 55118

### Time Periods

You may ask for different periods of the day by using phrases like:

    tomorrow morning     6am to 12pm
    Friday afternoon     12pm to 6pm
    Wednesday evening    6pm to 12am
    overnight Monday     12am to 6am (on Tuesday)
    Thursday             6am to 6pm
    Sunday night         6pm to 6am

## Usage Examples

### Current Conditions

Current conditions are available using phrases like:

    Ask Clima Cast for the weather.
    Ask Clima Cast for the current conditions in 55118.
    Ask Clima Cast what the humidity is in Baton Rouge, Louisiana?
    Ask Clima Cast what's the weather in Chicago, Illinois?

### Forecasts

You may get forecast information with phrases like:

    Ask Clima Cast for the forecast.
    Ask Clima Cast if it will be rainy in Saint Paul, Minnesota on Wednesday evening.
    Ask Clima Cast what the humidity will be on Monday afternoon in zip code 71301.
    Ask Clima Cast for the extended forecast in Seattle, Washington.

### Weather Alerts

To check for active alerts, use phrases like:

    Ask Clima Cast for the alerts.
    Ask Clima Cast, What are the alerts in Boise, Idaho?
    Ask Clima Cast, Are there any alerts?

## Configuration

### Setting Your Location

When you first use Clima Cast, you must set a default location by saying:

    Ask Clima Cast to set location to Boulder, Colorado.

### Voice Settings

You may also adjust the speed of the speech with:

    Ask Clima Cast to set the voice rate to 109 percent.

    Values lower than 100 percent will make the speech slower, while values above 100 percent will speed it up.

In addition, the speech pitch may be changed with:

    Ask Clima Cast to set the voice pitch to 79 percent.

    Values lower than 100 percent will make the voice deeper and values above 100 percent will make the voice higher.

### Custom Forecasts

You may also customize what gets reported in the forecast by adding and removing the different weather conditions using:

    Ask Clima Cast to remove the dew point from the custom forecast.
    Ask Clima Cast to add the humidity to the custom forecast.
    Ask Clima Cast to reset the custom forecast.

### Checking Settings

To get the current settings, use:

    Ask Clima Cast to get the settings
    Ask Clima Cast for the location
    Ask Clima Cast what's the pitch setting
    Ask Clima Cast for the rate
    Ask Clima Cast for the custom forecast

## Support

If you run into any issues or have a suggestion, send an email to: climaCast@homerow.net

## Acknowledgments

Clima Cast is not affiliated with the National Weather Service.
Location information is provided by HERE.com.

