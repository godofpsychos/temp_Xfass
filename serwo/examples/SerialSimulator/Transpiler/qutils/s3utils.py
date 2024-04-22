# OM NAMO GANAPATHAYEN NAMAHA
import boto3
import json
from dataclasses import dataclass
import re

@dataclass
class S3Arguments:
    filename: str
    bucket_name: str
    region: str
    key_id: str
    secret_access_key: str

def fetch_relevent_file_data(args: S3Arguments, filter_regex):
    s3 = boto3.resource('s3',
                    region_name=args.region,
                    aws_access_key_id=args.key_id,
                    aws_secret_access_key=args.secret_access_key)
    bucket = s3.Bucket(args.bucket_name)

    all_data = []
    for bucket_item in bucket.objects.all():
        if re.search(filter_regex, bucket_item) is not None:
            data_of_item = s3.get_object(Bucket=args.bucket_name, Key=args.filename)
            all_data.append(data_of_item)
    return all_data

def read_from_bucket(args: S3Arguments):
    s3 = boto3.resource('s3',
                    region_name=args.region,
                    aws_access_key_id=args.key_id,
                    aws_secret_access_key=args.secret_access_key)
    obj = s3.get_object(Bucket=args.bucket_name, Key=args.filename)
    if obj is None:
        return None
    data = json.loads(obj['Body'].read())
    return data

def write_to_bucket(args: S3Arguments, \
                    data: dict):
    s3 = boto3.resource('s3',
                        region_name=args.region,
                        aws_access_key_id=args.key_id,
                        aws_secret_access_key=args.secret_access_key)
    s3.Object(args.bucket_name, args.filename).put(Body=json.dumps(data))