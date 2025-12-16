import os
import tempfile
from typing import Optional, BinaryIO
from flask import current_app
import boto3
from botocore.exceptions import ClientError, BotoCoreError


class R2Storage:
    def __init__(self):
        self.account_id = current_app.config.get('R2_ACCOUNT_ID')
        self.access_key_id = current_app.config.get('R2_ACCESS_KEY_ID')
        self.secret_access_key = current_app.config.get('R2_SECRET_ACCESS_KEY')
        self.bucket_name = current_app.config.get('R2_BUCKET_NAME')
        self.public_url = current_app.config.get('R2_PUBLIC_URL')
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.bucket_name]):
            raise ValueError(
                "R2 credentials not configured. Please set R2_ACCOUNT_ID, "
                "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME environment variables."
            )
        
        endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name='auto'
        )
    
    def upload_file(self, file_obj: BinaryIO, object_key: str, content_type: Optional[str] = None) -> str:
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            if self.public_url:
                return f"{self.public_url.rstrip('/')}/{object_key}"
            else:
                return f"https://pub-{self.account_id}.r2.dev/{self.bucket_name}/{object_key}"
                
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to upload file to R2: {str(e)}")
    
    def download_file(self, object_key: str) -> bytes:
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response['Body'].read()
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to download file from R2: {str(e)}")
    
    def download_to_temp_file(self, object_key: str) -> str:
        file_content = self.download_file(object_key)
        
        suffix = os.path.splitext(object_key)[1] or ''
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(file_content)
        temp_file.close()
        
        return temp_file.name
    
    def delete_file(self, object_key: str) -> bool:
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to delete file from R2: {str(e)}")
    
    def file_exists(self, object_key: str) -> bool:
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Failed to check file existence in R2: {str(e)}")
    
    def get_presigned_url(self, object_key: str, expiration: int = 3600) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return url
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")


def get_r2_storage() -> R2Storage:
    return R2Storage()

