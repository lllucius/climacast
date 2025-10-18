# Deployment Guide

This guide explains how to deploy the Clima Cast Alexa skill using the new Alexa-hosted pattern.

## Deployment Options

### Option 1: Alexa-Hosted Skill (Recommended)

Alexa-hosted skills provide free hosting with AWS Lambda and S3 storage.

#### Steps:

1. **Create an Alexa-Hosted Skill**
   - Go to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
   - Click "Create Skill"
   - Enter skill name: "Clima Cast"
   - Choose "Custom" model
   - Choose "Alexa-Hosted (Python)" hosting
   - Click "Create skill"

2. **Clone Your Skill Repository**
   ```bash
   git clone <your-alexa-hosted-skill-repo-url>
   cd <your-skill-directory>
   ```

3. **Copy Project Files**
   ```bash
   # Copy lambda function
   cp -r /path/to/climacast/lambda/* lambda/
   
   # Copy skill package
   cp -r /path/to/climacast/skill-package/* skill-package/
   ```

4. **Configure Environment Variables**
   - In the Alexa Developer Console, go to "Code" tab
   - Add environment variables in the Lambda configuration:
     - `app_id`: Your skill's application ID (found in skill settings)
     - `mapquest_id`: Your MapQuest API key (get one at https://developer.mapquest.com/)
     - `event_id`: (Optional) SNS topic ARN for error notifications

5. **Create DynamoDB Tables**
   
   The skill requires four DynamoDB tables in us-east-1:
   
   - **LocationCache**: Stores geocoded locations
     - Partition key: `location` (String)
     - TTL attribute: `ttl`
   
   - **StationCache**: Stores weather station information
     - Partition key: `id` (String)
     - TTL attribute: `ttl`
   
   - **UserCache**: Stores user preferences
     - Partition key: `userid` (String)
     - No TTL (permanent storage)
   
   - **ZoneCache**: Stores NWS zone information
     - Partition key: `id` (String)
     - TTL attribute: `ttl`

   Create these tables using the AWS CLI or Console:
   ```bash
   aws dynamodb create-table \
     --table-name LocationCache \
     --attribute-definitions AttributeName=location,AttributeType=S \
     --key-schema AttributeName=location,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1

   aws dynamodb create-table \
     --table-name StationCache \
     --attribute-definitions AttributeName=id,AttributeType=S \
     --key-schema AttributeName=id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1

   aws dynamodb create-table \
     --table-name UserCache \
     --attribute-definitions AttributeName=userid,AttributeType=S \
     --key-schema AttributeName=userid,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1

   aws dynamodb create-table \
     --table-name ZoneCache \
     --attribute-definitions AttributeName=id,AttributeType=S \
     --key-schema AttributeName=id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1
   ```

   Enable TTL on appropriate tables:
   ```bash
   aws dynamodb update-time-to-live \
     --table-name LocationCache \
     --time-to-live-specification Enabled=true,AttributeName=ttl

   aws dynamodb update-time-to-live \
     --table-name StationCache \
     --time-to-live-specification Enabled=true,AttributeName=ttl

   aws dynamodb update-time-to-live \
     --table-name ZoneCache \
     --time-to-live-specification Enabled=true,AttributeName=ttl
   ```

6. **Update IAM Permissions**
   
   Ensure the Lambda execution role has permissions to access DynamoDB and SNS:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "dynamodb:GetItem",
           "dynamodb:PutItem",
           "dynamodb:Query",
           "dynamodb:BatchWriteItem"
         ],
         "Resource": [
           "arn:aws:dynamodb:us-east-1:*:table/LocationCache",
           "arn:aws:dynamodb:us-east-1:*:table/StationCache",
           "arn:aws:dynamodb:us-east-1:*:table/UserCache",
           "arn:aws:dynamodb:us-east-1:*:table/ZoneCache"
         ]
       },
       {
         "Effect": "Allow",
         "Action": [
           "sns:Publish"
         ],
         "Resource": "arn:aws:sns:*:*:*"
       }
     ]
   }
   ```

7. **Deploy**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push
   ```

8. **Test Your Skill**
   - Go to the "Test" tab in the Alexa Developer Console
   - Enable testing
   - Try: "Alexa, open Clima Cast"

### Option 2: Self-Hosted Lambda

If you prefer to host the Lambda function yourself:

1. **Install Dependencies**
   ```bash
   cd lambda
   pip install -r requirements.txt -t .
   ```

2. **Create Deployment Package**
   ```bash
   zip -r ../function.zip .
   ```

3. **Upload to Lambda**
   ```bash
   aws lambda update-function-code \
     --function-name climacast \
     --zip-file fileb://../function.zip
   ```

4. **Or use ASK CLI**
   ```bash
   ask deploy
   ```

## MapQuest API Key

The skill requires a MapQuest API key for geocoding. Get one for free at:
https://developer.mapquest.com/

Sign up and create an app to get your API key. The free tier allows 15,000 transactions per month.

## Updating the Skill

To update the skill after making changes:

```bash
git add .
git commit -m "Your update message"
git push
```

For self-hosted Lambda, repeat the deployment package creation and upload steps.

## Troubleshooting

### Skill Not Working
- Check CloudWatch Logs for errors
- Verify environment variables are set correctly
- Ensure DynamoDB tables exist and have correct permissions
- Verify MapQuest API key is valid

### "Location Not Found" Errors
- Check MapQuest API key
- Verify internet connectivity from Lambda
- Check CloudWatch logs for API errors

### Data Not Persisting
- Verify DynamoDB tables exist
- Check IAM permissions for DynamoDB access
- Ensure UserCache table does NOT have TTL enabled
