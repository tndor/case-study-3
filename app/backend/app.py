import os
import boto3
import random
import socket
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from botocore.exceptions import ClientError, NoCredentialsError
from prometheus_flask_exporter import PrometheusMetrics
from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, MODIFY_REPLACE

app = Flask(__name__)
metrics = PrometheusMetrics(app)
CORS(app)
load_dotenv()

# --- CONFIGURATION ---
DYNAMO_TABLE = os.getenv('DYNAMO_TABLE', '')
AWS_REGION = os.getenv('AWS_REGION', '')

# ACTIVE DIRECTORY CONFIG
AD_SERVER_IP = os.getenv('AD_SERVER_IP', '') 
AD_DOMAIN = os.getenv('AD_DOMAIN', '')
AD_USER = os.getenv('AD_USER', '') 
AD_PASSWORD = os.getenv('AD_PASSWORD', '') 

# --- AWS CLIENTS ---
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMO_TABLE)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    IS_MOCK_AWS = False
except (NoCredentialsError, ClientError):
    print("WARNING: No AWS Credentials found. AWS features will be MOCKED.")
    IS_MOCK_AWS = True

# --- HELPER: ACTIVE DIRECTORY CONNECTION ---
def get_ad_connection():
    """Establishes a connection to the Windows Server"""
    print(f"Attempting connection to AD at {AD_SERVER_IP}...")
    try:
        server = Server(AD_SERVER_IP, get_info=ALL, connect_timeout=5)
        conn = Connection(server, user=f'{AD_DOMAIN}\\{AD_USER}', password=AD_PASSWORD, authentication=SIMPLE, auto_bind=True)
        return conn
    except Exception as e:
        print(f"AD Connection Failed: {e}")
        return None

# --- WORKFLOW STEP 1: IDENTITY (AD) ---
def workflow_create_ad_user(username, first_name, last_name):
    conn = get_ad_connection()
    
    if not conn:
        return f"MOCK/ERROR: Could not reach Domain Controller at {AD_SERVER_IP}. (Check VPN/Security Group)"

    try:
        user_dn = f'CN={first_name} {last_name},CN=Users,DC=innovatech,DC=local'
        
        attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'sAMAccountName': username,
            'userPrincipalName': f'{username}@{AD_DOMAIN}',
            'givenName': first_name,
            'sn': last_name,
            'displayName': f'{first_name} {last_name}',
            'description': 'Provisioned via Innovatech HR K8s App'
        }
        
        print(f"Creating AD User: {user_dn}")
        
        if conn.add(user_dn, attributes=attributes):
            # FIX 2: Use strict syntax for modification
            # {'attribute': [(OPERATION, [VALUE])]}
            conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [512])]})
            
            # Set Password
            try:
                conn.extend.microsoft.modify_password(user_dn, 'Welcome123!')
                return f"AD: Successfully created user '{username}'"
            except Exception as pw_e:
                return f"AD: User created, but password set failed (Needs LDAPS): {pw_e}"
        else:
            result = str(conn.result)
            if "entryAlreadyExists" in result:
                return f"AD: User '{username}' already exists."
            return f"AD: Failed. {result}"
            
    except Exception as e:
        return f"AD Error: {str(e)}"

# --- WORKFLOW STEP 2: STORAGE (S3) ---
def workflow_create_home_folder(username):
    random_id = random.randint(1000, 9999)
    bucket_name = f"innovatech-home-{username}-{random_id}".lower()
    
    if IS_MOCK_AWS: return f"MOCK: Created S3 Bucket {bucket_name}"

    try:
        if AWS_REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
        return f"AWS: Provisioned S3 home folder '{bucket_name}'"
    except Exception as e:
        return f"AWS: S3 Error {str(e)}"

# --- WORKFLOW STEP 3: OFFBOARDING (AD DELETE) ---
def workflow_delete_ad_user(username, first_name, last_name):
    conn = get_ad_connection()
    if not conn: return "MOCK: AD Connection failed during delete."
    
    try:
        user_dn = f'CN={first_name} {last_name},CN=Users,DC=innovatech,DC=local'
        if conn.delete(user_dn):
            return f"AD: Deleted user '{username}'"
        else:
            return f"AD: Could not delete (Check if user exists): {conn.result}"
    except Exception as e:
        return f"AD Error: {e}"

# --- API ROUTES ---

@app.route('/employees', methods=['GET'])
def get_employees():
    if IS_MOCK_AWS:
        return jsonify([{'username': 'mock.user', 'department': 'Engineering', 'status': 'Active'}])
    try:
        response = table.scan()
        return jsonify(response.get('Items', []))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/onboard', methods=['POST'])
def onboard():
    data = request.json
    first = data.get('firstName')
    last = data.get('lastName')
    username = f"{first}.{last}".lower()
    
    logs = []
    
    # 1. Identity (Active Directory)
    ad_log = workflow_create_ad_user(username, first, last)
    logs.append(ad_log)
    
    # 2. Storage (AWS S3)
    s3_log = workflow_create_home_folder(username)
    logs.append(s3_log)
    
    # 3. State (DynamoDB)
    if not IS_MOCK_AWS:
        try:
            table.put_item(Item={
                'username': username,
                'firstName': first, 
                'lastName': last, 
                'department': data['department'], 
                'status': 'Active',
                'role': data['role']
            })
            logs.append(f"DB: Saved record for {username}")
        except Exception as e:
            logs.append(f"DB Error: {e}")
        
    return jsonify({"message": "Onboarding Complete", "steps": logs})

@app.route('/offboard', methods=['POST'])
def offboard():
    data = request.json
    username = data.get('username')
    
    logs = []
    first = "Unknown" 
    last = "Unknown"
    
    # 1. Fetch user details first (to get name for AD delete)
    if not IS_MOCK_AWS:
        try:
            resp = table.get_item(Key={'username': username})
            if 'Item' in resp:
                first = resp['Item']['firstName']
                last = resp['Item']['lastName']
        except Exception as e:
            logs.append(f"DB Error fetching user: {str(e)}")

    # 2. Decommission External Resources (AD & S3)
    # We still delete the access, even if we keep the DB record
    if first != "Unknown":
        logs.append(workflow_delete_ad_user(username, first, last))
        # Note: We didn't implement S3 delete in the latest iteration, 
        # but if you have it, it goes here.
    else:
        logs.append("AD: Skipped delete (Could not find name in DB)")

    # 3. SOFT DELETE: Mark as Inactive in DB instead of deleting
    if not IS_MOCK_AWS:
        try:
            table.update_item(
                Key={'username': username},
                UpdateExpression="set #s = :val",
                # 'status' is a reserved word in DynamoDB, so we alias it to #s
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':val': 'Inactive'}
            )
            logs.append(f"DB: Marked record {username} as Inactive")
        except Exception as e:
            logs.append(f"DB Error updating status: {str(e)}")

    return jsonify({"message": "Offboarding Complete", "logs": logs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)