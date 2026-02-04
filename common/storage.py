import aioboto3
from botocore.config import Config
from common.config import settings
from fastapi import UploadFile
import uuid
import os

class S3Storage:
    def __init__(self):
        self.bucket_name = settings.R2_BUCKET_NAME
        self.endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        self.access_key = settings.R2_ACCESS_KEY
        self.secret_key = settings.R2_SECRET_KEY
        self.session = aioboto3.Session()

    def _get_client_kwargs(self):
        return {
            "service_name": "s3",
            "endpoint_url": self.endpoint_url,
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "config": Config(signature_version="s3v4"),
            "region_name": "auto",
        }

    async def generate_upload_url(self, file_name: str, content_type: str, folder: str = "general"):
        """
        Generates a signed URL for the frontend to upload directly to R2.
        This saves server bandwidth.
        """
        unique_key = f"{folder}/{uuid.uuid4()}-{file_name}"
        
        async with self.session.client(**self._get_client_kwargs()) as s3:
            url = await s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": unique_key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,
            )
            return {"url": url, "key": unique_key}

    async def upload_file_direct(self, file: UploadFile, folder: str = "profiles") -> str:
        """
        Uploads a file directly from the backend to R2.
        Useful for small profile pictures or when the server needs to process the file first.
        """
        file_ext = os.path.splitext(file.filename)[1]
        unique_key = f"{folder}/{uuid.uuid4()}{file_ext}"
        
        async with self.session.client(**self._get_client_kwargs()) as s3:
            await s3.upload_fileobj(
                file.file,
                self.bucket_name,
                unique_key,
                ExtraArgs={"ContentType": file.content_type}
            )
            # This is the public URL format for Cloudflare R2
            # Replace 'pub-your-id.r2.dev' with your actual R2 Public Bucket URL or Custom Domain
            return f"https://media.meixup.com/{unique_key}"

    async def delete_file(self, file_key: str):
        """Removes a file from storage when a user deletes a post or profile picture."""
        async with self.session.client(**self._get_client_kwargs()) as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=file_key)

# Initialize a global storage instance
storage = S3Storage()