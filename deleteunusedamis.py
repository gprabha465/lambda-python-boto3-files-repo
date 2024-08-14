import json
import urllib.request
import boto3
import os
from dateutil.parser import parse
import datetime
age = os.environ['AGE']
used_ami = []
exception_ami_list = []

def lambda_handler(event, context):
    def days_old(date):
        get_date_obj = parse(date)
        date_obj = get_date_obj.replace(tzinfo=None)
        diff = datetime.datetime.now() - date_obj
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
        data["payload"]["summary"] = "Triggered by the rackspace_delete_ami_" + str(age) + "days lambda function - " + str(os.environ["env"])
        request_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, headers=headers, data=request_data)
        response = urllib.request.urlopen(request)
        response_content = response.read()
        print(response.getcode())
        ec2 = boto3.resource('ec2')
        instances = ec2.instances.all()
        for instance_id in instances:
            used_ami.append(instance_id.image.id)
        exception_ami_list = list(set(used_ami))

        ec2 = boto3.client('ec2')
        amis = ec2.describe_images(Owners=[
                'self'
            ])

        deleted_count = 0
        non_deleted_count = 0
        exception_list_ami_count = 0
        # initial_total_count = len(snap_response["Snapshots"])

        for ami in amis['Images']:
            create_date = ami['CreationDate']
            ami_id = ami['ImageId']
            day_old = days_old(create_date)
            if day_old > int(age):
                try:
                    if ami_id in exception_ami_list:
                        print(f"{ami_id} exists in the exception list and shouldnt be deleted")
                        exception_list_ami_count += 1
                    else:
                        #deregister the AMI
                        print ("deleting -> " + ami_id + " - create_date = " + create_date)
                        ec2.deregister_image(ImageId=ami_id)
                        deleted_count += 1
                except:
                    print(f"The {ami_id} cannot be deleted")
                    non_deleted_count += 1

        data["payload"]["custom_details"]["Body"] = "lambda funtion execution completed. Deleted AMIs  " + str(deleted_count) + ", non deleted AMIs " + str(non_deleted_count) + ", AMIs in exception list " + str(exception_list_ami_count)
        data["payload"]["summary"] = "Triggered by the rackspace_delete_ami_" + str(age) + "days lambda function - " + str(os.environ["env"])
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
        data["payload"]["summary"] = "Triggered by the rackspace_delete_ami_" + str(age) + "days lambda function - " + str(os.environ["env"])
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
