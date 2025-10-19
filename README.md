# Clima Cast
NWS API based weather Alexa skill (Version 2.1)

Using information provided by the National Weather Service, Clima Cast gives you the current conditions and the 7-day forecast for your area or any other United States city.

## What's New in Version 2.1

**Major Refactoring** - Removed all backwards compatibility code and fully embraced ASK SDK patterns. The lambda function now uses individual intent handlers with consolidated weather logic. See [SKILLBUILDER_REFACTORING.md](SKILLBUILDER_REFACTORING.md) for details.

**Key improvements:**
- ✨ Individual handler classes for each intent (14 handlers)
- 🏗️ Idiomatic ASK SDK SkillBuilder pattern
- 🗑️ Removed 446 lines (14.5% code reduction)
- ⚡ Faster execution without adapter layers
- 🧪 More maintainable and testable code structure
- 📖 All weather logic consolidated in BaseIntentHandler
- 🔒 Security verified (0 vulnerabilities)

## What's New in Version 2.0

This was a major refactoring that modernized the skill to use the current Alexa-hosted pattern and the latest NWS API endpoints. See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for complete details.

**Key improvements:**
- 🎯 Modern Alexa-hosted skill structure with ASK SDK support
- 🔄 Updated to NWS API v3 JSON endpoints
- 📦 Simplified deployment with git push for hosted skills
- 📚 Comprehensive documentation (deployment, testing, migration)
- 🔧 Better dependency management with requirements.txt
- 🐛 Bug fixes and code improvements

For migration from v1.x, see [MIGRATION.md](MIGRATION.md).

## Project Structure

This project follows the Alexa-hosted skill pattern:

- `lambda/` - Lambda function code and dependencies
- `skill-package/` - Skill metadata and interaction model
  - `skill.json` - Skill manifest
  - `interactionModels/custom/` - Interaction models by locale
- `skill/` - Original skill definition files (reference only)
- `tests/` - Test files
- `aniso8601/`, `requests/`, `aws-lambda-lxml/` - Vendored dependencies (optional, for environments without pip)

## Setup and Deployment

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

**Quick Start for Alexa-Hosted Skills:**

1. Create an Alexa-hosted skill in the Alexa Developer Console
2. Copy files from `lambda/` to your skill's lambda directory
3. Copy files from `skill-package/` to your skill's skill-package directory
4. Set up environment variables (see DEPLOYMENT.md)
5. Create DynamoDB tables (see DEPLOYMENT.md)
6. Push changes with git

**Quick Start for Self-Hosted Lambda:**

1. Run `./upload` to create and deploy the Lambda package
2. Deploy interaction model with ASK CLI: `ask deploy`
3. Set up environment variables and DynamoDB tables

For complete instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Requirements

- Python 3.8+
- MapQuest API key (free tier available)
- AWS account for DynamoDB table
- Single DynamoDB table: climacast_persistence (for Alexa-hosted persistent attributes)

## Usage

When asking for specific weather conditions, you may use:

    temperature or temp
    wind chill
    heat index
    dew point
    barometric pressure or pressure
    relative humidity or humidity
    precipitation, rain chance, snow chance, chance of rain or chance of snow
    wind

When using a location, you may use either the city name and state or the zip code, like:

    Boulder, Colorado
    55118
    zip code 55118

You may ask for different periods of the day by using phrases like:

    tomorrow morning     6am to 12pm
    Friday afternoon     12pm to 6pm
    Wednesday evening    6pm to 12am
    overnight Monday     12am to 6am (on Tuesday)
    Thursday             6am to 6pm
    Sunday night         6pm to 6am

Current conditions are available using phrases like:

    Ask Clima Cast for the weather.
    Ask Clima Cast for the current conditions in 55118.
    Ask Clima Cast what the humidity is in Baton Rouge, Louisiana?
    Ask Clima Cast what's the weather in Chicago, Illinois?

You may get forecast information with phrases like:

    Ask Clima Cast for the forecast.
    Ask Clima Cast if it will be rainy in Saint Paul, Minnesota on Wednesday evening.
    Ask Clima Cast what the humidity will be on Monday afternoon in zip code 71301.
    Ask Clima Cast for the extended forecast in Seattle, Washington.

To check for active alerts, use phrases like:

    Ask Clima Cast for the alerts.
    Ask Clima Cast, What are the alerts in Boise, Idaho?
    Ask Clima Cast, Are there any alerts?

When you first use Clima Cast, you must set a default location by saying:

    Ask Clima Cast to set location to Boulder, Colorado.

You may also adjust the speed of the speech with:

    Ask Clima Cast to set the voice rate to 109 percent.

    Values lower than 100 percent will make the speech slower, while values above 100 percent will speed it up.

In addition, the speech pitch may be changed with:

    Ask Clima Cast to set the voice pitch to 79 percent.

    Values lower than 100 percent will make the voice deeper and values above 100 percent will make the voice higher.

You may also customize what gets reported in the forecast by adding and removing the different weather conditions using:

    Ask Clima Cast to remove the dew point from the custom forecast.
    Ask Clima Cast to add the humidity to the custom forecast.
    Ask Clima Cast to reset the custom forecast.

To get the current settings, use:

    Ask Clima Cast to get the settings
    Ask Clima Cast for the location
    Ask Clima Cast what's the pitch setting
    Ask Clima Cast for the rate
    Ask Clima Cast for the custom forecast

If you run into any issues or have a suggestion, send an email to: clima Cast@homerow.net

Source code is available at: https://github.com/lllucius/climacast

Clima Cast is not affiliated with the National Weather Service.
Location information is provided by Mapzen.

