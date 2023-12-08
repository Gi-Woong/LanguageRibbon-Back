import boto3
from botocore.client import Config
from config.settings import ENV

aws_access_key_id = ENV("AWS_ACCESS_KEY_ID")
aws_secret_access_key = ENV("AWS_SECRET_ACCESS_KEY")

s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    config=Config(signature_version='s3v4'),
    region_name="ap-northeast-2"
)

bucket_name = ENV("S3_BUCKET_NAME")