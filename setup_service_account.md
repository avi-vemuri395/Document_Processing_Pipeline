# Service Account Setup for Document AI

## Steps to Create Service Account

1. **Go to Service Accounts page**:
   https://console.cloud.google.com/iam-admin/serviceaccounts?project=robotic-heaven-469117-v3

2. **Create Service Account**:
   - Click "CREATE SERVICE ACCOUNT"
   - Name: `docai-processor`
   - Description: `Service account for Document AI processing`
   - Click "CREATE AND CONTINUE"

3. **Grant Permissions**:
   - Role: `Document AI API User` (or `Document AI Viewer`)
   - Click "CONTINUE"
   - Click "DONE"

4. **Create Key**:
   - Click on the service account you just created
   - Go to "KEYS" tab
   - Click "ADD KEY" → "Create new key"
   - Choose "JSON"
   - Save the downloaded file

5. **Setup Credentials**:
   ```bash
   # Create credentials directory
   mkdir -p credentials
   
   # Move the downloaded JSON file
   mv ~/Downloads/robotic-heaven-*.json credentials/docai-service-account.json
   
   # Update .env file to use service account
   # Uncomment the GOOGLE_APPLICATION_CREDENTIALS line
   ```

6. **Update .env**:
   Uncomment this line in your .env file:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./credentials/docai-service-account.json
   ```

## Quick Test

After setup, run:
```bash
python scripts/verify_docai_setup.py
```