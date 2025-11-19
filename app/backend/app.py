import os
import boto3
from flask import Flask, request, jsonify
from flask_cors import CORS
from botocore.exceptions import ClientError, NoCredentialsError

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for React

# --- CONFIGURATION ---
DYNAMO_TABLE = os.environ.get('DYNAMO_TABLE', 'Innovatech_Employees')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# --- AWS CLIENTS ---
# We use try/except to allow the code to run in 'Mock Mode' if you don't have keys set up yet
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMO_TABLE)
    iam_client = boto3.client('iam', region_name=AWS_REGION)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    IS_MOCK = False
except (NoCredentialsError, ClientError):
    print("WARNING: No AWS Credentials found. Running in MOCK mode.")
    IS_MOCK = True

IS_MOCK = True
# --- WORKFLOW HELPERS ---

def workflow_create_iam_user(username):
    """Step 2 of Onboarding: Identity Management"""
    if IS_MOCK: return "MOCK: Created IAM User " + username
    
    try:
        iam_client.create_user(UserName=username)
        # In a real app, you would also add them to a group:
        # iam_client.add_user_to_group(GroupName='Developers', UserName=username)
        return f"AWS: Created IAM User '{username}'"
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            return f"AWS: IAM User '{username}' already exists."
        raise e

def workflow_create_home_folder(username):
    """Step 3 of Onboarding: File Server / Home Folder"""
    bucket_name = f"innovatech-home-{username}".lower()
    if IS_MOCK: return f"MOCK: Created S3 Bucket {bucket_name}"

    try:
        s3_client.create_bucket(Bucket=bucket_name)
        return f"AWS: Provisioned S3 home folder '{bucket_name}'"
    except ClientError as e:
        return f"AWS: Failed to create S3 bucket (might exist or permission issue)"

def workflow_delete_user(username):
    """Offboarding Workflow"""
    if IS_MOCK: return f"MOCK: Deleted IAM User {username}"
    
    try:
        # Note: To delete a user, you must first delete their login profiles, keys, etc.
        # This is a simplified version for the assignment.
        iam_client.delete_user(UserName=username)
        return f"AWS: Deleted IAM User '{username}'"
    except ClientError:
        return f"AWS: User '{username}' not found or could not be deleted"

# --- API ROUTES ---

@app.route('/employees', methods=['GET'])
def get_employees():
    """Fetch all employees from DynamoDB"""
    if IS_MOCK:
        return jsonify([
            {'username': 'alice.wonder', 'department': 'Engineering', 'status': 'Active'},
            {'username': 'bob.builder', 'department': 'Construction', 'status': 'Active'}
        ])
    
    try:
        response = table.scan()
        return jsonify(response.get('Items', []))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/onboard', methods=['POST'])
def onboard_employee():
    """
    THE MAIN WORKFLOW:
    1. Generate Username
    2. Update DB (HR Record)
    3. Create IAM User (Identity)
    4. Create S3 Bucket (Storage)
    """
    data = request.json
    first = data.get('firstName', '').lower()
    last = data.get('lastName', '').lower()
    username = f"{first}.{last}"
    
    workflow_logs = []

    # 1. DB Entry
    item = {
        'username': username,
        'firstName': data['firstName'],
        'lastName': data['lastName'],
        'department': data['department'],
        'status': 'Active',
        'role': data['role']
    }
    
    try:
        # Step 1: Database
        if not IS_MOCK:
            table.put_item(Item=item)
        workflow_logs.append(f"DB: Registered employee record for {username}")

        # Step 2: IAM Provisioning
        iam_log = workflow_create_iam_user(username)
        workflow_logs.append(iam_log)

        # Step 3: Home Folder Provisioning
        s3_log = workflow_create_home_folder(username)
        workflow_logs.append(s3_log)

        return jsonify({
            "message": f"Onboarding complete for {username}",
            "steps": workflow_logs
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/offboard', methods=['POST'])
def offboard_employee():
    data = request.json
    username = data.get('username')
    
    try:
        # Step 1: Remove from DB
        if not IS_MOCK:
            table.delete_item(Key={'username': username})
        
        # Step 2: Remove Identity
        iam_log = workflow_delete_user(username)
        
        return jsonify({
            "message": "Offboarding successful",
            "logs": [f"DB: Removed record {username}", iam_log]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)