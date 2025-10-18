# Migration Guide

This guide helps you migrate from the legacy Alexa skill structure to the new Alexa-hosted pattern.

## Overview of Changes

### Version 1.x (Legacy)
- Single `lambda_function.py` in root directory
- Manual Lambda deployment with zip files
- Legacy interaction model files in `skill/` directory
- Vendored dependencies (`requests/`, `aniso8601/`, `aws-lambda-lxml/`)
- Custom deployment script

### Version 2.0 (Current)
- Organized `lambda/` directory structure
- ASK SDK for Python support
- Modern interaction model in `skill-package/`
- Dependencies managed via `requirements.txt`
- Support for both Alexa-hosted and self-hosted deployment
- Updated NWS API endpoints (removed deprecated XML endpoints)

## Breaking Changes

### 1. Directory Structure
**Old:**
```
climacast/
├── lambda_function.py
├── skill/
│   └── intent_schema.json
├── requests/
├── aniso8601/
└── upload
```

**New:**
```
climacast/
├── lambda/
│   ├── lambda_function.py
│   └── requirements.txt
├── skill-package/
│   ├── skill.json
│   └── interactionModels/custom/en-US.json
└── upload
```

### 2. Deployment Process

**Old:** Manual zip and AWS CLI upload
```bash
./upload
```

**New:** 
- Alexa-hosted: `git push`
- Self-hosted: `./upload` or `ask deploy`

### 3. Dependencies

**Old:** Vendored in repository
- Bundled `requests`, `aniso8601`, `lxml`
- Large repository size
- Manual updates

**New:** Managed via pip
- Defined in `requirements.txt`
- Smaller repository
- Easy updates

### 4. API Changes

**Old:** Mixed XML and JSON APIs
```python
obs = Observations(event, stations)  # Uses XML endpoints
```

**New:** JSON API only
```python
obs = Observationsv3(event, stations)  # Uses JSON API
```

## Migration Steps

### For Existing Self-Hosted Skills

1. **Backup Current Deployment**
   ```bash
   # Download current Lambda function
   aws lambda get-function --function-name climacast --query 'Code.Location' --output text | xargs curl -o backup.zip
   ```

2. **Update Local Repository**
   ```bash
   git pull origin main
   git checkout -b migrate-to-v2
   ```

3. **Install Dependencies**
   ```bash
   cd lambda
   pip install -r requirements.txt -t .
   ```

4. **Test Locally** (Optional)
   ```bash
   # Set environment variables
   export app_id="your-app-id"
   export mapquest_id="your-mapquest-key"
   
   # Run test
   python3 lambda_function.py ../tests/test_location
   ```

5. **Deploy**
   ```bash
   cd ..
   ./upload
   ```

6. **Update Interaction Model**
   ```bash
   ask deploy --target skill-metadata
   ask deploy --target model
   ```

7. **Test the Skill**
   - Open Alexa Developer Console
   - Go to Test tab
   - Test various commands

### For New Alexa-Hosted Skills

1. **Create Alexa-Hosted Skill**
   - Go to Alexa Developer Console
   - Create new skill
   - Choose "Alexa-Hosted (Python)"

2. **Clone Skill Repository**
   ```bash
   git clone <your-alexa-skill-repo-url>
   cd <skill-name>
   ```

3. **Copy Files**
   ```bash
   # Copy from this repository
   cp -r /path/to/climacast/lambda/* lambda/
   cp -r /path/to/climacast/skill-package/* skill-package/
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "Migrate to Clima Cast v2"
   git push
   ```

5. **Configure**
   - Set environment variables in Lambda configuration
   - Create DynamoDB tables (see DEPLOYMENT.md)
   - Update IAM permissions

### For Existing Alexa-Hosted Skills

If you already have an Alexa-hosted skill:

1. **Update Files**
   ```bash
   # In your skill repository
   rm -rf lambda/*
   rm -rf skill-package/*
   
   # Copy new files
   cp -r /path/to/climacast/lambda/* lambda/
   cp -r /path/to/climacast/skill-package/* skill-package/
   ```

2. **Update Dependencies**
   - The `requirements.txt` will be automatically processed by Alexa-hosted skills
   - Dependencies are installed on deployment

3. **Deploy**
   ```bash
   git add .
   git commit -m "Update to Clima Cast v2"
   git push
   ```

## Compatibility

### Backward Compatibility

The new `lambda_function.py` maintains backward compatibility:
- Can run without ASK SDK (falls back to legacy handler)
- Existing DynamoDB schemas unchanged
- User settings preserved
- Location cache compatible

### Forward Compatibility

To ensure future compatibility:
- Use `requirements.txt` for dependency management
- Follow Alexa-hosted skill structure
- Use modern NWS JSON API endpoints
- Use ASK SDK when available

## Troubleshooting Migration Issues

### Issue: Lambda Package Too Large

**Problem:** Deployment package exceeds Lambda size limit

**Solution:**
```bash
# Use Lambda Layers for large dependencies
cd lambda
pip install -r requirements.txt -t ./python
zip -r9 layer.zip python
aws lambda publish-layer-version \
  --layer-name climacast-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.8 python3.9 python3.10 python3.11
```

### Issue: Import Errors

**Problem:** Module not found errors

**Solution:**
```bash
# Ensure all dependencies are installed
cd lambda
pip install -r requirements.txt -t .

# Or use the vendored dependencies
export PYTHONPATH=../requests:../aniso8601:../aws-lambda-lxml/3.6.4/py36:$PYTHONPATH
```

### Issue: DynamoDB Access Denied

**Problem:** Lambda can't access DynamoDB tables

**Solution:**
- Verify tables exist in us-east-1
- Update Lambda execution role with DynamoDB permissions
- Check table names match code expectations

### Issue: Interaction Model Mismatch

**Problem:** Intent names not recognized

**Solution:**
```bash
# Redeploy interaction model
ask deploy --target model --force
```

### Issue: Environment Variables Not Set

**Problem:** Skill can't access environment variables

**Solution:**
- For Lambda: Set in AWS Console under Configuration > Environment variables
- For Alexa-hosted: Set in Developer Console under Code > Environment variables

## Rolling Back

If you need to roll back to the previous version:

### Self-Hosted Lambda
```bash
# Restore from backup
aws lambda update-function-code \
  --function-name climacast \
  --zip-file fileb://backup.zip
```

### Alexa-Hosted
```bash
# Revert git commit
git revert HEAD
git push
```

### Interaction Model
```bash
# Use ASK CLI to restore previous version
ask api get-skill-manifest --skill-id <skill-id> > previous-manifest.json
ask api update-skill-manifest --skill-id <skill-id> --manifest-file previous-manifest.json
```

## Data Migration

### User Data
No migration needed - user preferences stored in DynamoDB remain compatible.

### Cache Data
No migration needed - location and station caches use same schema.

### Configuration
- Copy environment variables to new Lambda configuration
- Verify MapQuest API key is set
- Update SNS topic ARN if using notifications

## Post-Migration Checklist

- [ ] Skill responds to launch request
- [ ] Location setting works
- [ ] Current weather retrieval works
- [ ] Forecast queries work
- [ ] Alerts are accessible
- [ ] User settings persist
- [ ] Voice rate/pitch customization works
- [ ] Custom forecast configuration works
- [ ] All slot types recognized
- [ ] Error handling works correctly

## Getting Help

If you encounter issues during migration:

1. Check CloudWatch Logs for error details
2. Review DEPLOYMENT.md for setup requirements
3. Verify all environment variables are set
4. Test with simple requests first (e.g., launch request)
5. Open an issue on GitHub with error details

## Future Updates

To stay updated with future versions:
- Watch the GitHub repository
- Subscribe to release notifications
- Follow the changelog
- Test in development environment before production deployment
