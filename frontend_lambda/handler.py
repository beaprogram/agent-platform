import os

import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["SITE_BUCKET"]


def handler(event, context):
    obj = s3.get_object(Bucket=BUCKET, Key="index.html")
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": obj["Body"].read().decode("utf-8"),
    }
