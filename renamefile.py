import boto3
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def lambda_handler(event, context):
    source_bucket_name = 'praneethlambda'
    source_folder = 'receivedfiles/'  # Update this to your source folder name
    target_folder = 'renamedfiles/'  # Update this to your target folder name
    
    # Check if the event contains 'Records'
    if 'Records' not in event or not event['Records']:
        return {
            'statusCode': 400,
            'body': 'Event structure is incorrect or missing.'
        }
    
    key = event['Records'][0]['s3']['object']['key']
    logger.info("Event: " + json.dumps(event))
    
    # Ensure the file is in the source folder
    if not key.startswith(source_folder):
        logger.info(f"File {key} is not in the source folder, skipping.")
        return {
            'statusCode': 200,
            'body': f'File {key} is not in the source folder, skipping.'
        }
    
    # Get the filename and extension
    file_name, file_extension = os.path.splitext(os.path.basename(key))
    
    # Generate a new filename with the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    new_file_name = f'{file_name}-{timestamp}{file_extension}'
    
    # Define the new key for the target folder
    new_key = f'{target_folder}{new_file_name}'
    
    # Copy the object to the new key in the target folder and delete the old one from the source folder
    copy_source = {'Bucket': source_bucket_name, 'Key': key}
    try:
        s3.copy_object(CopySource=copy_source, Bucket=source_bucket_name, Key=new_key)
        s3.delete_object(Bucket=source_bucket_name, Key=key)
        logger.info(f"File moved and renamed from {key} to {new_key}")
        
        return {
            'statusCode': 200,
            'body': f'File moved and renamed from {key} to {new_key} in bucket {source_bucket_name}'
        }
    except Exception as e:
        logger.error(f"Error moving and renaming file {key}: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error moving and renaming file {key}: {str(e)}'
        }
