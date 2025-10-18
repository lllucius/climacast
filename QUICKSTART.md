# Quick Start Guide

Get Clima Cast up and running quickly!

## For New Alexa-Hosted Skills (Easiest)

### 1. Create Skill (5 minutes)
```bash
# In Alexa Developer Console:
1. Click "Create Skill"
2. Name: "Clima Cast"
3. Choose: "Custom" model
4. Choose: "Alexa-Hosted (Python)"
5. Click "Create skill"
```

### 2. Get MapQuest API Key (2 minutes)
```bash
1. Go to https://developer.mapquest.com/
2. Sign up (free)
3. Create an app
4. Copy your API key
```

### 3. Deploy Code (5 minutes)
```bash
# Clone your skill's repo
git clone <your-alexa-hosted-repo-url>
cd <your-skill-name>

# Copy files from Clima Cast
git remote add climacast https://github.com/lllucius/climacast.git
git fetch climacast
git checkout climacast/copilot/refactor-alexa-skill-pattern -- lambda skill-package

# Commit and push
git add .
git commit -m "Deploy Clima Cast v2"
git push
```

### 4. Configure (5 minutes)
```bash
# In Alexa Developer Console > Code tab:
# Add environment variables:
app_id=<your-skill-application-id>  # Found in Build tab
mapquest_id=<your-mapquest-key>
```

### 5. Create DynamoDB Tables (5 minutes)
```bash
# Run these AWS CLI commands:
for table in LocationCache StationCache UserCache ZoneCache; do
  aws dynamodb create-table \
    --table-name $table \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 2>/dev/null || echo "$table exists"
done

# Enable TTL (except UserCache)
for table in LocationCache StationCache ZoneCache; do
  aws dynamodb update-time-to-live \
    --table-name $table \
    --time-to-live-specification Enabled=true,AttributeName=ttl 2>/dev/null
done

# Note: UserCache uses 'userid' as partition key, others use 'id' or 'location'
# Adjust create-table commands as needed
```

### 6. Test (2 minutes)
```bash
# In Developer Console > Test tab:
"open clima cast"
"set location to Boulder Colorado"
"what's the weather"
```

**Total Time: ~25 minutes**

---

## For Self-Hosted Lambda (Traditional)

### 1. Prerequisites
```bash
# Install AWS CLI and ASK CLI
pip install awscli ask-cli

# Configure AWS
aws configure

# Configure ASK CLI
ask configure
```

### 2. Clone and Setup
```bash
# Clone repository
git clone https://github.com/lllucius/climacast.git
cd climacast

# Install dependencies
cd lambda
pip install -r requirements.txt -t .
cd ..
```

### 3. Create Lambda Function
```bash
# Create function
aws lambda create-function \
  --function-name climacast \
  --runtime python3.11 \
  --role arn:aws:iam::<account>:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --environment Variables="{app_id=<skill-id>,mapquest_id=<mapquest-key>}"
```

### 4. Deploy Code
```bash
# Use the upload script
./upload
```

### 5. Deploy Interaction Model
```bash
# Deploy skill manifest and model
ask deploy
```

### 6. Create DynamoDB Tables
```bash
# Same as Alexa-hosted (see above)
```

### 7. Test
```bash
# In Developer Console > Test tab or:
ask dialog --locale en-US
```

---

## Common Issues

### "Location not found"
- **Cause:** MapQuest API key not set or invalid
- **Fix:** Verify `mapquest_id` environment variable

### "Observation data unavailable"
- **Cause:** NWS station has no recent data
- **Fix:** Try a different location or wait

### "DynamoDB access denied"
- **Cause:** Lambda role lacks permissions
- **Fix:** Add DynamoDB permissions to execution role

### Skill won't invoke
- **Cause:** Interaction model not deployed
- **Fix:** Deploy model with `ask deploy --target model`

---

## Next Steps

After getting it running:

1. **Customize Settings**
   - "set the voice rate to 110 percent"
   - "set the voice pitch to 90 percent"

2. **Set Up Custom Forecast**
   - "add wind to the custom forecast"
   - "remove dew point from the custom forecast"

3. **Try Different Queries**
   - "what's the weather tomorrow afternoon"
   - "will it rain on Friday in Seattle Washington"
   - "are there any alerts"

4. **Read Documentation**
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment details
   - [TESTING.md](TESTING.md) - Testing guide
   - [README.md](README.md) - Feature documentation

---

## Development Workflow

### Making Changes

```bash
# Create feature branch
git checkout -b my-feature

# Make changes in lambda/lambda_function.py

# Test locally (if dependencies installed)
cd lambda
python3 lambda_function.py ../tests/test_location

# Commit and push
git add .
git commit -m "Add feature"
git push  # Alexa-hosted: automatic deployment
# OR
./upload  # Self-hosted: manual deployment
```

### Debugging

```bash
# Check CloudWatch Logs
aws logs tail /aws/lambda/climacast --follow

# Test specific request
cd lambda
python3 -c "
import lambda_function
import json
event = json.load(open('../tests/test_location'))
print(lambda_function.lambda_handler(event, None))
"
```

---

## Useful Commands

```bash
# View skill status
ask api get-skill-status --skill-id <skill-id>

# Get skill manifest
ask api get-skill-manifest --skill-id <skill-id>

# View interaction model
ask api get-interaction-model --skill-id <skill-id> --locale en-US

# Check Lambda logs
aws logs tail /aws/lambda/climacast --since 10m

# Query DynamoDB
aws dynamodb scan --table-name UserCache --limit 5

# Test geocoding
curl "https://www.mapquestapi.com/geocoding/v1/address?key=<KEY>&location=Boulder+Colorado"

# Test NWS API
curl "https://api.weather.gov/points/40.0150,-105.2705"
```

---

## Getting Help

- 📧 Email: climacast@homerow.net
- 💬 GitHub Issues: https://github.com/lllucius/climacast/issues
- 📖 Full Docs: [DEPLOYMENT.md](DEPLOYMENT.md)
- 🔄 Migration: [MIGRATION.md](MIGRATION.md)

---

## Resources

- [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
- [ASK SDK for Python Docs](https://alexa-skills-kit-python-sdk.readthedocs.io/)
- [NWS API Documentation](https://www.weather.gov/documentation/services-web-api)
- [MapQuest Geocoding API](https://developer.mapquest.com/documentation/geocoding-api/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
