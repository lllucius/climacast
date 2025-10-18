# Changelog

All notable changes to the Clima Cast Alexa skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-10-18

### Added
- Individual ASK SDK intent handler classes for all 18 intents
- BaseIntentHandler class with comprehensive weather functionality:
  - `parse_when()` - Parse time/date from slots
  - `get_alerts()` - Retrieve weather alerts
  - `get_current()` - Get current conditions
  - `get_forecast()` - Get forecast data
  - `get_extended()` - Get extended forecast
  - `get_location_from_slots()` - Process location input
- SKILLBUILDER_REFACTORING.md documentation explaining the new architecture
- Custom lambda_handler wrapper to support both Alexa and DataLoad events

### Changed
- **BREAKING**: Replaced generic SkillRequestHandler adapter with individual intent handlers
- **BREAKING**: Removed all backwards compatibility code (Skill class and FUNCS dictionary)
- Refactored intent routing to use SkillBuilder.add_request_handler() for each intent
- Intent handlers now directly extend AbstractRequestHandler
- Handler registration now explicit in SkillBuilder (14 individual handlers)
- Lambda handler now created via SkillBuilder.lambda_handler() with custom wrapper
- MetricIntentHandler and GetSettingIntentHandler refactored to use BaseIntentHandler methods directly
- All weather logic consolidated into BaseIntentHandler for better organization

### Removed
- **Skill class entirely** (715 lines of backwards compatibility code)
- **FUNCS dictionary** (23 lines of obsolete routing)
- Generic SkillRequestHandler adapter class (109 lines)
- Event conversion logic between ASK SDK and old format
- Total reduction: 446 lines (14.5% smaller codebase)

### Improved
- Better separation of concerns with one handler per intent
- More maintainable and testable code structure
- Idiomatic ASK SDK code following best practices
- Clearer intent handling logic
- Direct method calls without indirection
- Faster execution (no unnecessary object creation or format conversion)
- Easier to add new intents or modify existing ones
- All weather logic in one centralized location

### Security
- CodeQL analysis: 0 vulnerabilities detected

## [2.0.0] - 2024-10-18

### Added
- ASK SDK for Python support
- Modern Alexa-hosted skill directory structure (`lambda/`, `skill-package/`)
- Comprehensive deployment guide (DEPLOYMENT.md)
- Migration guide for upgrading from v1.x (MIGRATION.md)
- Testing guide with unit and integration test examples (TESTING.md)
- Modern interaction model in JSON format (en-US.json)
- Skill manifest file (skill.json) for Alexa skill configuration
- Support for both Alexa-hosted and self-hosted deployment options
- Lambda function README with API documentation
- Updated .gitignore for modern development workflow

### Changed
- **BREAKING**: Migrated from XML observation endpoints to NWS JSON API v3
  - Now uses `Observationsv3` class with `/stations/{id}/observations` endpoint
  - Removed `w1.weather.gov/xml/current_obs/` endpoint
  - Removed `w1.weather.gov/data/obhistory/` endpoint
- **BREAKING**: Requires ASK SDK for Python
- Reorganized project structure to follow Alexa-hosted skill pattern
- Updated deployment script to work with new directory structure
- Dependencies now managed via `requirements.txt`
- Updated User-Agent header to "ClimacastAlexaSkill/2.0"
- Bumped VERSION constant from 1 to 2
- Updated README with quick start guides for both deployment options
- Updated requirements.txt with compatible ASK SDK versions

### Fixed
- Duplicate station iteration loop in `Observationsv3.__init__` method
- Regex syntax warning in `get_discussion` method (added raw string prefix)
- Improved error handling for ASK SDK request/response conversion

### Removed
- XML-based `Observations` class (use `Observationsv3` instead)
- Old directory structure (root-level lambda_function.py)
- Bundled dependencies in favor of `requirements.txt`
- XML observation endpoints

### Security
- Updated to use modern NWS API endpoints with better error handling
- Improved input validation for ASK SDK request conversion
- Updated dependencies to latest compatible versions

## [1.0.0] - Previous Release

### Features
- Initial release with NWS V3 API support
- Current weather conditions from NWS observation stations
- 7-day forecast using NWS gridpoint data
- Active weather alerts for user's area
- Customizable voice rate and pitch
- Customizable forecast metrics
- Support for city/state and zip code locations
- Location geocoding via MapQuest API
- DynamoDB caching for locations, stations, zones, and user preferences
- Time-based forecast queries (e.g., "tomorrow afternoon")
- Extended forecast support
- Barometric pressure trend analysis
- Multi-metric weather queries
- ZIP code recognition and handling

### Intents
- LaunchRequest - Welcome message
- MetricIntent - Get weather metrics
- GetSettingIntent - Get current settings
- SetLocationIntent - Set default location
- SetRateIntent - Set voice rate
- SetPitchIntent - Set voice pitch
- GetCustomIntent - Get custom forecast configuration
- AddCustomIntent - Add metric to custom forecast
- RemCustomIntent - Remove metric from custom forecast
- RstCustomIntent - Reset custom forecast to defaults
- AMAZON.CancelIntent - Cancel current operation
- AMAZON.HelpIntent - Get help information
- AMAZON.StopIntent - Stop the skill

### Supported Metrics
- Temperature (current and forecast)
- Wind chill
- Heat index
- Dew point
- Barometric pressure
- Relative humidity
- Precipitation chance and amount
- Snow amount
- Wind speed and direction
- Wind gusts
- Sky conditions
- Weather summary

### NWS API Endpoints Used
- `/points/{lat},{lon}` - Get grid data
- `/gridpoints/{office}/{x},{y}` - Get forecast data
- `/stations/{stationId}/observations` - Get observations (v3 JSON API)
- `/zones/{type}/{zoneId}` - Get zone information
- `/alerts/active` - Get active weather alerts
- `/products/types/{type}/locations/{cwa}` - Get weather products
- `w1.weather.gov/xml/current_obs/{station}.xml` - Legacy XML observations
- `w1.weather.gov/data/obhistory/{station}.html` - Legacy observation history

## Migration from 1.x to 2.0

See [MIGRATION.md](MIGRATION.md) for detailed migration instructions.

### Key Migration Steps
1. Update directory structure (move files to `lambda/` and `skill-package/`)
2. Install dependencies via `requirements.txt`
3. Update deployment process (git push for Alexa-hosted, or new upload script)
4. Verify DynamoDB tables and permissions
5. Test thoroughly in development environment

### Compatibility Notes
- User data in DynamoDB is fully compatible (no migration needed)
- Existing user preferences and location settings preserved
- Voice rate/pitch settings maintained
- Custom forecast configurations unchanged
- Cache data (locations, stations, zones) compatible

## Known Issues

### Version 2.0
- MapQuest API occasionally returns unexpected location results for ambiguous names
- Some NWS observation stations may have incomplete or null data fields
- Voice recognition may confuse similar city names (e.g., "Woodberry" vs "Woodbury")
- DynamoDB TTL cleanup can take up to 48 hours to remove expired items

### Version 1.x
- All issues from 1.x plus:
- Using deprecated XML observation endpoints
- No ASK SDK support
- Manual dependency management

## Roadmap

### Planned Features
- [ ] Support for metric units (Celsius, km/h, mm)
- [ ] Multiple location profiles per user
- [ ] Weather comparison between locations
- [ ] Historical weather data
- [ ] Severe weather push notifications
- [ ] Integration with NOAA weather radios
- [ ] Support for marine forecasts
- [ ] Support for fire weather forecasts
- [ ] Pollen and air quality data
- [ ] Sunrise/sunset times
- [ ] Moon phase information

### Technical Improvements
- [ ] Unit test coverage
- [ ] Integration test suite
- [ ] CI/CD pipeline
- [ ] Performance monitoring
- [ ] Automated dependency updates
- [ ] API rate limiting
- [ ] Response caching optimization
- [ ] Error recovery improvements
- [ ] Logging enhancements

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

## License

This project is licensed under the GNU Affero GPL - see the LICENSE file for details.

## Credits

- Weather data provided by the National Weather Service (NWS)
- Location geocoding provided by MapQuest
- Built with Amazon Alexa Skills Kit
- Original author: Leland Lucius

## Support

For issues, questions, or suggestions:
- Email: climacast@homerow.net
- GitHub Issues: https://github.com/lllucius/climacast/issues
- Source Code: https://github.com/lllucius/climacast
