import os
import boto3
import random
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from botocore.exceptions import ClientError, NoCredentialsError

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for React
load_dotenv()  # Load environment variables from .env file

# --- CONFIGURATION ---
DYNAMO_TABLE = os.getenv('DYNAMO_TABLE', '')
AWS_REGION = os.getenv('AWS_REGION', '')

print(f"Using AWS Region: {AWS_REGION}, DynamoDB Table: {DYNAMO_TABLE}")

# --- AWS CLIENTS ---
# We use try/except to allow the code to run in 'Mock Mode' if you don't have keys set up yet
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMO_TABLE)
    iam_client = boto3.client('iam', region_name=AWS_REGION)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    IS_MOCK = False
except Exception as e:
    print("WARNING: No AWS Credentials found. Running in MOCK mode.", e)
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

def workflow_create_home_folder(bucket_name):
    """Step 3: File Server / Home Folder"""
    if IS_MOCK: return f"MOCK: Created S3 Bucket {bucket_name}"

    try:
        # Handle Region Constraints
        if AWS_REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        return f"AWS: Provisioned S3 home folder '{bucket_name}'"
    except ClientError as e:
        print(f"FULL S3 ERROR: {e}")
        return f"AWS: Failed to create S3 bucket {bucket_name}. Error: {e}"

def workflow_delete_home_folder(bucket_name):
    """Helper to empty and delete an S3 bucket"""
    if not bucket_name: return "AWS: No bucket name recorded, skipping S3 delete."
    if IS_MOCK: return f"MOCK: Deleted S3 Bucket {bucket_name}"

    try:
        # 1. S3 buckets must be empty before deletion. Delete all objects first.
        # We list objects and delete them in batches.
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={ 'Objects': objects_to_delete }
            )
            print(f"Emptied bucket {bucket_name}")

        # 2. Delete the bucket itself
        s3_client.delete_bucket(Bucket=bucket_name)
        return f"AWS: Decommissioned S3 home folder '{bucket_name}'"
    except ClientError as e:
        # If bucket doesn't exist (NoSuchBucket), we consider it a success (idempotent)
        if e.response['Error']['Code'] == 'NoSuchBucket':
             return f"AWS: Bucket '{bucket_name}' already deleted."
        return f"AWS: Failed to delete bucket '{bucket_name}'. Error: {e}"

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
    data = request.json
    first = data.get('firstName', '').lower()
    last = data.get('lastName', '').lower()
    username = f"{first}.{last}"
    
    # Generate the bucket name HERE so we can save it to the DB
    random_id = random.randint(1000, 9999)
    bucket_name = f"innovatech-home-{username}-{random_id}".lower()
    
    workflow_logs = []

    item = {
        'username': username,
        'firstName': data['firstName'],
        'lastName': data['lastName'],
        'department': data['department'],
        'status': 'Active',
        'role': data['role'],
        'homeFolder': bucket_name  # <--- Save this for offboarding later!
    }
    
    try:
        # Step 1: IAM Provisioning (Identity)
        # Commented out as per your request (permissions issue)
        iam_log = "SKIPPED: IAM User Creation (Permissions restricted)"
        # iam_log = workflow_create_iam_user(username) 
        workflow_logs.append(iam_log)

        # Step 2: Home Folder Provisioning (Storage)
        s3_log = workflow_create_home_folder(bucket_name)
        workflow_logs.append(s3_log)

        # Step 3: Database Record (State)
        # We save LAST so we only record success if previous steps didn't crash hard
        if not IS_MOCK:
            table.put_item(Item=item)
        workflow_logs.append(f"DB: Registered employee record for {username}")

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
    workflow_logs = []
    
    try:
        # Step 1: Get details from DB to find their specific bucket name
        bucket_name = None
        if not IS_MOCK:
            response = table.get_item(Key={'username': username})
            if 'Item' in response:
                bucket_name = response['Item'].get('homeFolder')
                
                # Fallback: If user was created before we started saving bucket names, 
                # we try to find a bucket that matches the pattern.
                if not bucket_name:
                    try:
                        all_buckets = s3_client.list_buckets()
                        prefix = f"innovatech-home-{username}-"
                        for b in all_buckets.get('Buckets', []):
                            if b['Name'].startswith(prefix):
                                bucket_name = b['Name']
                                break
                    except: pass

        # Step 2: Delete S3 Bucket
        if bucket_name:
            s3_log = workflow_delete_home_folder(bucket_name)
            workflow_logs.append(s3_log)
        else:
            workflow_logs.append("AWS: No S3 bucket found for this user.")

        # Step 3: Remove Identity
        # Commented out based on your 'onboard' logic, but left active here 
        # just in case the user exists. It won't break if user is missing.
        iam_log = workflow_delete_user(username)
        workflow_logs.append(iam_log)

        # Step 4: Remove from DB
        if not IS_MOCK:
            table.delete_item(Key={'username': username})
        workflow_logs.append(f"DB: Removed record {username}")
        
        return jsonify({
            "message": "Offboarding successful",
            "logs": workflow_logs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)