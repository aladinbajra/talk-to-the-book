"""
Storage service for file management.
"""
import os
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageService:
    """Service for storing and retrieving files."""
    
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.storage_path = Path(settings.STORAGE_PATH)
        
        if self.storage_type == "s3":
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION
            )
            self.s3_bucket = settings.S3_BUCKET
    
    async def store_file(
        self,
        book_id: str,
        filename: str,
        content: bytes,
        file_format: str
    ) -> str:
        """Store a file and return its path."""
        if self.storage_type == "local":
            # Local storage
            book_dir = self.storage_path / "books" / book_id
            book_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = book_dir / f"original.{file_format}"
            file_path.write_bytes(content)
            
            return str(file_path)
        
        elif self.storage_type == "s3":
            # S3 storage
            key = f"books/{book_id}/original.{file_format}"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=content
            )
            return key
        
        else:
            raise ValueError(f"Unknown storage type: {self.storage_type}")
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve a file."""
        if self.storage_type == "local":
            return Path(file_path).read_bytes()
        
        elif self.storage_type == "s3":
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=file_path
            )
            return response["Body"].read()
        
        else:
            raise ValueError(f"Unknown storage type: {self.storage_type}")
    
    async def delete_book(self, book_id: str):
        """Delete all files for a book."""
        if self.storage_type == "local":
            book_dir = self.storage_path / "books" / book_id
            if book_dir.exists():
                import shutil
                shutil.rmtree(book_dir)
        
        elif self.storage_type == "s3":
            # List and delete all objects with prefix
            prefix = f"books/{book_id}/"
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix)
            
            for page in pages:
                if "Contents" in page:
                    objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                    self.s3_client.delete_objects(
                        Bucket=self.s3_bucket,
                        Delete={"Objects": objects}
                    )
