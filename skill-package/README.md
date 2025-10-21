# Skill Package

This directory contains the Alexa skill definition using the modern Skill Package API format.

## Structure

```
skill-package/
├── skill.json                          # Skill manifest with metadata
└── interactionModels/
    └── custom/
        └── en-US.json                  # Interaction model for US English locale
```

## Files

### skill.json

The skill manifest contains:
- Publishing information (name, description, keywords)
- Skill category and distribution settings
- API endpoint configuration (Lambda ARN)
- Privacy and compliance information

### interactionModels/custom/en-US.json

The interaction model for the US English locale contains:
- Invocation name: "clima cast"
- Intent definitions with sample utterances
- Custom slot type definitions

## Custom Slot Types

The interaction model defines the following custom slot types:

- **TYPE_DAY** - Day numbers (first, second, 1st, 2nd, etc.)
- **TYPE_LEADIN** - Phrase starters for questions (what is the, what's the, etc.)
- **TYPE_METRIC** - Weather metrics (temperature, humidity, pressure, etc.)
- **TYPE_MONTH** - Month names (january, february, etc.)
- **TYPE_SETTING** - Skill settings (location, pitch, rate)
- **TYPE_WHEN_ABS** - Absolute time references (monday, tuesday morning, etc.)
- **TYPE_WHEN_ANY** - Any time reference (includes absolute plus relative like tomorrow)
- **TYPE_WHEN_POS** - Possessive time references (monday's, tomorrow's, etc.)
- **TYPE_ZIP_CONN** - Connectors for zip codes (in zip code, for zip code, etc.)

## Intents

The skill supports the following intents:

### Built-in Intents
- **AMAZON.CancelIntent** - Cancel the current interaction
- **AMAZON.HelpIntent** - Request help
- **AMAZON.StopIntent** - Stop the skill

### Custom Intents
- **MetricIntent** - Get weather metrics for various times and locations
- **GetSettingIntent** - Get current skill settings
- **SetRateIntent** - Set speech rate
- **SetPitchIntent** - Set speech pitch
- **SetLocationIntent** - Set default location
- **GetCustomIntent** - Get custom forecast settings
- **AddCustomIntent** - Add metric to custom forecast
- **RemCustomIntent** - Remove metric from custom forecast
- **RstCustomIntent** - Reset custom forecast to default

## Deployment

To deploy this skill:

1. Install ASK CLI: `npm install -g ask-cli`
2. Configure credentials: `ask configure`
3. Deploy the skill: `ask deploy`

Or use the ASK CLI v2:
```bash
ask smapi create-skill --manifest "file:skill-package/skill.json"
```

## Migration Notes

This skill package was migrated from the legacy format that used:
- `intent_schema.json` - Converted to interaction model intents
- `utterances` - Converted to intent samples in interaction model
- `type_*` files - Converted to slot type definitions in interaction model
- `upload` script - Removed (replaced by ASK CLI deployment)

The modern format provides:
- Better version control
- Easier multi-locale support
- Integration with ASK CLI
- JSON schema validation
- Consistent structure with other Alexa skills
