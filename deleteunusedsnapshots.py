import json
import urllib.request
import boto3
import os
from dateutil.parser import parse
from datetime import datetime
age = os.environ['AGE']
current_date = datetime.strftime(datetime.today(),"%Y,%m,%d")

def lambda_handler(event, context):
    def days_old(date):
        get_date_obj = parse(date)
        date_obj = get_date_obj.replace(tzinfo=None)
        diff = datetime.now() - date_obj
        return diff.days

    def get_secret():
        secret_name = os.environ['secret_name']
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager')
        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            secret_value = response['SecretString']
        else:
            secret_value = response['SecretBinary']
        return secret_value
    url = "https://events.pagerduty.com/v2/enqueue"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "payload": {
            "summary": "",
            "severity": "info",
            "source": "lambda-aws@tsb.com",
            "custom_details" : {
              "From" : "lambda",
              "Body" : ""
            }
            },
        "routing_key": "",
        "event_action": "trigger",
        "links": [
            {
                "href": "http://pagerduty.example.com",
                "text": "An example link."
            }
        ],
        "images": [
            {
                "src": "https://www.google.com/url?sa=i&url=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FAWS_Lambda&psig=AOvVaw3qconxBeS0zhj-HNf--F8U&ust=1683698751659000&source=images&cd=vfe&ved=0CBEQjRxqFwoTCJjQkeHI5_4CFQAAAAAdAAAAABAI",
                "alt": "An example link with an image"
            }
        ]
    }


    try:
        data["routing_key"] = json.loads(get_secret())["routing_key"]
        data["payload"]["custom_details"]["Body"]= "lambda funtion execution started"
        data["payload"]["summary"] = "Triggered by the rackspace_delete_snapshot_" + str(age) + "days lambda function - " + str(os.environ["env"])
        request_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, headers=headers, data=request_data)
        response = urllib.request.urlopen(request)
        response_content = response.read()
        print(response.getcode())
        # print(json.loads(response_content))
        ec2 = boto3.client('ec2')
        snap_response = ec2.describe_snapshots(OwnerIds=['self'])

        deleted_count = 0
        non_deleted_count = 0
        # initial_total_count = len(snap_response["Snapshots"])

        for snapshot in snap_response["Snapshots"]:
            snap_id = snapshot['SnapshotId']
            snap_created = snapshot['StartTime']
            old = datetime.strftime(snapshot['StartTime'], "%Y%m%d")
            diff_days = days_old(old)
            try:
                if diff_days > int(age):
                    print(f"Deleting {snap_id} created on {snap_created}")
                    ec2.delete_snapshot(SnapshotId=snap_id)
                    deleted_count += 1
            except Exception as e:
                non_deleted_count += 1
                print(f"The snapshot {snap_id} is already in use. Error: {e}")

        data["payload"]["custom_details"]["Body"] = "lambda funtion execution completed. Deleted Snapshots " + str(deleted_count) + " non deleted snapshots " + str(non_deleted_count)
        data["payload"]["summary"] = "Triggered by the rackspace_delete_snapshot_" + str(age) + "days lambda function - " + str(os.environ["env"])
        request_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, headers=headers, data=request_data)
        try:
            response = urllib.request.urlopen(request)
            response_content = response.read()
            print(response.getcode())
            # print(json.loads(response_content))
        except urllib.request.HTTPError as e:
            print(e.getcode())
            print(e.read())

    except Exception as e:
        print(f"Error during execution: {e}")
        data["routing_key"] = json.loads(get_secret())["routing_key"]
        data["payload"]["custom_details"]["Body"]= "lambda funtion execution failed. Reason: " + str(e)
        data["payload"]["summary"] = "Triggered by the rackspace_delete_snapshot_" + str(age) + "days lambda function - " + str(os.environ["env"])
        request_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, headers=headers, data=request_data)
        try:
            response = urllib.request.urlopen(request)
            response_content = response.read()
            print(response.getcode())
            # print(json.loads(response_content))
        except urllib.request.HTTPError as e:
            print(e.getcode())
            print(e.read())
