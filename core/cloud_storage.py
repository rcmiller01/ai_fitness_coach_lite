"""
Cloud Storage Integration for AI Fitness Coach

Provides unified cloud storage interface supporting multiple providers:
- AWS S3
- Google Cloud Storage
- Azure Blob Storage
- Local filesystem fallback

Handles user data, plugin downloads, and media files.
"""

import os
import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Union, BinaryIO
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes

class StorageProvider(Enum):
    """Supported cloud storage providers"""
    AWS_S3 = "aws_s3"
    GOOGLE_CLOUD = "google_cloud"
    AZURE_BLOB = "azure_blob"
    LOCAL_FS = "local_fs"

@dataclass
class StorageConfig:
    """Cloud storage configuration"""
    provider: StorageProvider = StorageProvider.LOCAL_FS
    
    # AWS S3 Configuration
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_bucket: str = ""
    
    # Google Cloud Configuration
    gcp_credentials_path: str = ""
    gcp_bucket: str = ""
    gcp_project_id: str = ""
    
    # Azure Configuration
    azure_connection_string: str = ""
    azure_container: str = ""
    
    # Local filesystem
    local_storage_path: str = "storage"
    
    # General settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: List[str] = None
    enable_compression: bool = True
    enable_encryption: bool = False

@dataclass
class StorageObject:
    """Represents a stored object"""
    key: str
    size: int
    content_type: str
    last_modified: datetime
    etag: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class CloudStorageManager:
    """Unified cloud storage management system"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.provider = None
        self.logger = logging.getLogger(__name__)
        
        # Folder structure
        self.folders = {
            "user_data": "users/{user_id}/data/",
            "user_uploads": "users/{user_id}/uploads/",
            "plugins": "plugins/",
            "plugin_downloads": "plugins/downloads/",
            "workout_exports": "users/{user_id}/exports/",
            "backups": "backups/",
            "media": "media/",
            "temp": "temp/"
        }
        
    async def initialize(self) -> bool:
        """Initialize cloud storage provider"""
        try:
            if self.config.provider == StorageProvider.AWS_S3:
                return await self._init_aws_s3()
            elif self.config.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._init_google_cloud()
            elif self.config.provider == StorageProvider.AZURE_BLOB:
                return await self._init_azure_blob()
            else:
                return self._init_local_fs()
        except Exception as e:
            self.logger.error(f"Failed to initialize storage provider: {e}")
            # Fallback to local filesystem
            return self._init_local_fs()
    
    async def _init_aws_s3(self) -> bool:
        """Initialize AWS S3 storage"""
        try:
            import aioboto3
            
            self.session = aioboto3.Session(
                aws_access_key_id=self.config.aws_access_key_id,
                aws_secret_access_key=self.config.aws_secret_access_key,
                region_name=self.config.aws_region
            )
            
            # Test connection
            async with self.session.client('s3') as s3:
                await s3.head_bucket(Bucket=self.config.aws_bucket)
            
            self.provider = StorageProvider.AWS_S3
            self.logger.info("✅ AWS S3 storage initialized")
            return True
            
        except ImportError:
            self.logger.warning("aioboto3 not available, falling back to local storage")
            return self._init_local_fs()
        except Exception as e:
            self.logger.error(f"AWS S3 initialization failed: {e}")
            return self._init_local_fs()
    
    async def _init_google_cloud(self) -> bool:
        """Initialize Google Cloud Storage"""
        try:
            from google.cloud import storage
            import aiofiles
            
            if self.config.gcp_credentials_path and os.path.exists(self.config.gcp_credentials_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.gcp_credentials_path
            
            self.gcp_client = storage.Client(project=self.config.gcp_project_id)
            self.gcp_bucket = self.gcp_client.bucket(self.config.gcp_bucket)
            
            # Test connection
            self.gcp_bucket.reload()
            
            self.provider = StorageProvider.GOOGLE_CLOUD
            self.logger.info("✅ Google Cloud Storage initialized")
            return True
            
        except ImportError:
            self.logger.warning("google-cloud-storage not available, falling back to local storage")
            return self._init_local_fs()
        except Exception as e:
            self.logger.error(f"Google Cloud Storage initialization failed: {e}")
            return self._init_local_fs()
    
    async def _init_azure_blob(self) -> bool:
        """Initialize Azure Blob Storage"""
        try:
            from azure.storage.blob.aio import BlobServiceClient
            
            self.azure_client = BlobServiceClient.from_connection_string(
                self.config.azure_connection_string
            )
            
            # Test connection
            async with self.azure_client:
                container_client = self.azure_client.get_container_client(
                    self.config.azure_container
                )
                await container_client.get_container_properties()
            
            self.provider = StorageProvider.AZURE_BLOB
            self.logger.info("✅ Azure Blob Storage initialized")
            return True
            
        except ImportError:
            self.logger.warning("azure-storage-blob not available, falling back to local storage")
            return self._init_local_fs()
        except Exception as e:
            self.logger.error(f"Azure Blob Storage initialization failed: {e}")
            return self._init_local_fs()
    
    def _init_local_fs(self) -> bool:
        """Initialize local filesystem storage"""
        try:
            storage_path = Path(self.config.local_storage_path)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Create folder structure
            for folder_name, folder_path in self.folders.items():
                # Remove placeholder patterns for local setup
                clean_path = folder_path.replace("{user_id}", "default_user")
                full_path = storage_path / clean_path
                full_path.mkdir(parents=True, exist_ok=True)
            
            self.provider = StorageProvider.LOCAL_FS
            self.logger.info("✅ Local filesystem storage initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Local filesystem initialization failed: {e}")
            return False
    
    async def upload_file(self, file_data: bytes, key: str, content_type: str = None,
                         metadata: Dict[str, Any] = None) -> bool:
        """Upload file to storage"""
        try:
            # Validate file
            if not self._validate_file(file_data, key):
                return False
            
            # Auto-detect content type
            if content_type is None:
                content_type, _ = mimetypes.guess_type(key)
                if content_type is None:
                    content_type = "application/octet-stream"
            
            # Add default metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "uploaded_at": datetime.now().isoformat(),
                "original_size": len(file_data),
                "checksum": hashlib.md5(file_data).hexdigest()
            })
            
            # Compress if enabled
            if self.config.enable_compression and self._should_compress(key):
                file_data = await self._compress_data(file_data)
                metadata["compressed"] = True
            
            # Upload based on provider
            if self.provider == StorageProvider.AWS_S3:
                return await self._upload_s3(file_data, key, content_type, metadata)
            elif self.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._upload_gcp(file_data, key, content_type, metadata)
            elif self.provider == StorageProvider.AZURE_BLOB:
                return await self._upload_azure(file_data, key, content_type, metadata)
            else:
                return await self._upload_local(file_data, key, content_type, metadata)
                
        except Exception as e:
            self.logger.error(f"File upload failed: {e}")
            return False
    
    async def download_file(self, key: str) -> Optional[bytes]:
        """Download file from storage"""
        try:
            if self.provider == StorageProvider.AWS_S3:
                return await self._download_s3(key)
            elif self.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._download_gcp(key)
            elif self.provider == StorageProvider.AZURE_BLOB:
                return await self._download_azure(key)
            else:
                return await self._download_local(key)
                
        except Exception as e:
            self.logger.error(f"File download failed: {e}")
            return None
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from storage"""
        try:
            if self.provider == StorageProvider.AWS_S3:
                return await self._delete_s3(key)
            elif self.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._delete_gcp(key)
            elif self.provider == StorageProvider.AZURE_BLOB:
                return await self._delete_azure(key)
            else:
                return await self._delete_local(key)
                
        except Exception as e:
            self.logger.error(f"File deletion failed: {e}")
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[StorageObject]:
        """List files in storage"""
        try:
            if self.provider == StorageProvider.AWS_S3:
                return await self._list_s3(prefix, limit)
            elif self.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._list_gcp(prefix, limit)
            elif self.provider == StorageProvider.AZURE_BLOB:
                return await self._list_azure(prefix, limit)
            else:
                return await self._list_local(prefix, limit)
                
        except Exception as e:
            self.logger.error(f"File listing failed: {e}")
            return []
    
    async def get_file_info(self, key: str) -> Optional[StorageObject]:
        """Get file metadata"""
        try:
            if self.provider == StorageProvider.AWS_S3:
                return await self._get_info_s3(key)
            elif self.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._get_info_gcp(key)
            elif self.provider == StorageProvider.AZURE_BLOB:
                return await self._get_info_azure(key)
            else:
                return await self._get_info_local(key)
                
        except Exception as e:
            self.logger.error(f"Get file info failed: {e}")
            return None
    
    async def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for file access"""
        try:
            if self.provider == StorageProvider.AWS_S3:
                return await self._presigned_url_s3(key, expiration)
            elif self.provider == StorageProvider.GOOGLE_CLOUD:
                return await self._presigned_url_gcp(key, expiration)
            elif self.provider == StorageProvider.AZURE_BLOB:
                return await self._presigned_url_azure(key, expiration)
            else:
                # Local filesystem doesn't support presigned URLs
                return f"/storage/download/{key}"
                
        except Exception as e:
            self.logger.error(f"Presigned URL generation failed: {e}")
            return None
    
    # Helper methods for building storage paths
    def get_user_data_path(self, user_id: str, filename: str) -> str:
        """Get storage path for user data"""
        return self.folders["user_data"].format(user_id=user_id) + filename
    
    def get_user_upload_path(self, user_id: str, filename: str) -> str:
        """Get storage path for user uploads"""
        return self.folders["user_uploads"].format(user_id=user_id) + filename
    
    def get_plugin_path(self, plugin_id: str, filename: str) -> str:
        """Get storage path for plugin files"""
        return self.folders["plugins"] + f"{plugin_id}/{filename}"
    
    def get_plugin_download_path(self, plugin_id: str, version: str) -> str:
        """Get storage path for plugin downloads"""
        return self.folders["plugin_downloads"] + f"{plugin_id}_v{version}.zip"
    
    def get_workout_export_path(self, user_id: str, filename: str) -> str:
        """Get storage path for workout exports"""
        return self.folders["workout_exports"].format(user_id=user_id) + filename
    
    def get_backup_path(self, filename: str) -> str:
        """Get storage path for backups"""
        return self.folders["backups"] + filename
    
    # Provider-specific implementation methods
    async def _upload_s3(self, file_data: bytes, key: str, content_type: str, metadata: Dict) -> bool:
        """Upload to AWS S3"""
        try:
            async with self.session.client('s3') as s3:
                await s3.put_object(
                    Bucket=self.config.aws_bucket,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata={k: str(v) for k, v in metadata.items()}
                )
            return True
        except Exception as e:
            self.logger.error(f"S3 upload failed: {e}")
            return False
    
    async def _download_s3(self, key: str) -> Optional[bytes]:
        """Download from AWS S3"""
        try:
            async with self.session.client('s3') as s3:
                response = await s3.get_object(Bucket=self.config.aws_bucket, Key=key)
                data = await response['Body'].read()
                
                # Decompress if needed
                if response.get('Metadata', {}).get('compressed') == 'True':
                    data = await self._decompress_data(data)
                
                return data
        except Exception as e:
            self.logger.error(f"S3 download failed: {e}")
            return None
    
    async def _delete_s3(self, key: str) -> bool:
        """Delete from AWS S3"""
        try:
            async with self.session.client('s3') as s3:
                await s3.delete_object(Bucket=self.config.aws_bucket, Key=key)
            return True
        except Exception as e:
            self.logger.error(f"S3 deletion failed: {e}")
            return False
    
    async def _list_s3(self, prefix: str, limit: int) -> List[StorageObject]:
        """List files in AWS S3"""
        try:
            objects = []
            async with self.session.client('s3') as s3:
                response = await s3.list_objects_v2(
                    Bucket=self.config.aws_bucket,
                    Prefix=prefix,
                    MaxKeys=limit
                )
                
                for obj in response.get('Contents', []):
                    objects.append(StorageObject(
                        key=obj['Key'],
                        size=obj['Size'],
                        content_type="application/octet-stream",  # S3 doesn't return content type in list
                        last_modified=obj['LastModified'],
                        etag=obj['ETag'].strip('"')
                    ))
            
            return objects
        except Exception as e:
            self.logger.error(f"S3 listing failed: {e}")
            return []
    
    async def _get_info_s3(self, key: str) -> Optional[StorageObject]:
        """Get file info from AWS S3"""
        try:
            async with self.session.client('s3') as s3:
                response = await s3.head_object(Bucket=self.config.aws_bucket, Key=key)
                
                return StorageObject(
                    key=key,
                    size=response['ContentLength'],
                    content_type=response.get('ContentType', 'application/octet-stream'),
                    last_modified=response['LastModified'],
                    etag=response['ETag'].strip('"'),
                    metadata=response.get('Metadata', {})
                )
        except Exception as e:
            self.logger.error(f"S3 get info failed: {e}")
            return None
    
    async def _presigned_url_s3(self, key: str, expiration: int) -> Optional[str]:
        """Generate presigned URL for AWS S3"""
        try:
            async with self.session.client('s3') as s3:
                url = await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.config.aws_bucket, 'Key': key},
                    ExpiresIn=expiration
                )
            return url
        except Exception as e:
            self.logger.error(f"S3 presigned URL failed: {e}")
            return None
    
    # Local filesystem implementations
    async def _upload_local(self, file_data: bytes, key: str, content_type: str, metadata: Dict) -> bool:
        """Upload to local filesystem"""
        try:
            file_path = Path(self.config.local_storage_path) / key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Write metadata
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            with open(metadata_path, 'w') as f:
                json.dump({
                    'content_type': content_type,
                    'metadata': metadata
                }, f)
            
            return True
        except Exception as e:
            self.logger.error(f"Local upload failed: {e}")
            return False
    
    async def _download_local(self, key: str) -> Optional[bytes]:
        """Download from local filesystem"""
        try:
            file_path = Path(self.config.local_storage_path) / key
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Check if compressed
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    file_meta = json.load(f)
                    if file_meta.get('metadata', {}).get('compressed'):
                        data = await self._decompress_data(data)
            
            return data
        except Exception as e:
            self.logger.error(f"Local download failed: {e}")
            return None
    
    async def _delete_local(self, key: str) -> bool:
        """Delete from local filesystem"""
        try:
            file_path = Path(self.config.local_storage_path) / key
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            
            if file_path.exists():
                file_path.unlink()
            
            if metadata_path.exists():
                metadata_path.unlink()
            
            return True
        except Exception as e:
            self.logger.error(f"Local deletion failed: {e}")
            return False
    
    async def _list_local(self, prefix: str, limit: int) -> List[StorageObject]:
        """List files in local filesystem"""
        try:
            objects = []
            storage_path = Path(self.config.local_storage_path)
            
            if prefix:
                search_path = storage_path / prefix
            else:
                search_path = storage_path
            
            count = 0
            for file_path in search_path.rglob('*'):
                if count >= limit:
                    break
                
                if file_path.is_file() and not file_path.suffix == '.meta':
                    relative_path = file_path.relative_to(storage_path)
                    
                    # Get metadata
                    metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
                    content_type = "application/octet-stream"
                    
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r') as f:
                                file_meta = json.load(f)
                                content_type = file_meta.get('content_type', content_type)
                        except:
                            pass
                    
                    objects.append(StorageObject(
                        key=str(relative_path),
                        size=file_path.stat().st_size,
                        content_type=content_type,
                        last_modified=datetime.fromtimestamp(file_path.stat().st_mtime)
                    ))
                    count += 1
            
            return objects
        except Exception as e:
            self.logger.error(f"Local listing failed: {e}")
            return []
    
    async def _get_info_local(self, key: str) -> Optional[StorageObject]:
        """Get file info from local filesystem"""
        try:
            file_path = Path(self.config.local_storage_path) / key
            
            if not file_path.exists():
                return None
            
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            content_type = "application/octet-stream"
            metadata = {}
            
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        file_meta = json.load(f)
                        content_type = file_meta.get('content_type', content_type)
                        metadata = file_meta.get('metadata', {})
                except:
                    pass
            
            stat = file_path.stat()
            
            return StorageObject(
                key=key,
                size=stat.st_size,
                content_type=content_type,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                metadata=metadata
            )
        except Exception as e:
            self.logger.error(f"Local get info failed: {e}")
            return None
    
    # Utility methods
    def _validate_file(self, file_data: bytes, key: str) -> bool:
        """Validate file before upload"""
        # Check file size
        if len(file_data) > self.config.max_file_size:
            self.logger.error(f"File too large: {len(file_data)} > {self.config.max_file_size}")
            return False
        
        # Check file extension
        if self.config.allowed_extensions:
            file_ext = Path(key).suffix.lower().lstrip('.')
            if file_ext not in self.config.allowed_extensions:
                self.logger.error(f"File extension not allowed: {file_ext}")
                return False
        
        return True
    
    def _should_compress(self, key: str) -> bool:
        """Check if file should be compressed"""
        compressible_types = {'.txt', '.json', '.csv', '.log', '.sql', '.xml', '.html', '.css', '.js'}
        return Path(key).suffix.lower() in compressible_types
    
    async def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip"""
        import gzip
        return gzip.compress(data)
    
    async def _decompress_data(self, data: bytes) -> bytes:
        """Decompress gzipped data"""
        import gzip
        return gzip.decompress(data)

# Storage factory function
def create_storage_manager(config: Optional[StorageConfig] = None) -> CloudStorageManager:
    """Create storage manager with configuration"""
    if config is None:
        # Load from environment variables
        provider_name = os.getenv("STORAGE_PROVIDER", "local_fs").lower()
        
        try:
            provider = StorageProvider(provider_name)
        except ValueError:
            provider = StorageProvider.LOCAL_FS
        
        config = StorageConfig(
            provider=provider,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            aws_region=os.getenv("AWS_S3_REGION", "us-east-1"),
            aws_bucket=os.getenv("AWS_S3_BUCKET", ""),
            gcp_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            gcp_bucket=os.getenv("GCP_STORAGE_BUCKET", ""),
            gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
            azure_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
            azure_container=os.getenv("AZURE_STORAGE_CONTAINER", ""),
            local_storage_path=os.getenv("LOCAL_STORAGE_PATH", "storage")
        )
    
    return CloudStorageManager(config)

# Usage example and testing
async def test_storage_manager():
    """Test the storage manager"""
    config = StorageConfig(
        provider=StorageProvider.LOCAL_FS,
        local_storage_path="test_storage"
    )
    
    storage = CloudStorageManager(config)
    await storage.initialize()
    
    # Test upload
    test_data = b"Hello, World! This is a test file."
    key = storage.get_user_data_path("test_user", "test.txt")
    
    success = await storage.upload_file(test_data, key, "text/plain")
    print(f"Upload success: {success}")
    
    # Test download
    downloaded = await storage.download_file(key)
    print(f"Downloaded: {downloaded.decode() if downloaded else 'Failed'}")
    
    # Test list
    files = await storage.list_files("users/")
    print(f"Files found: {len(files)}")
    
    # Test delete
    deleted = await storage.delete_file(key)
    print(f"Delete success: {deleted}")

if __name__ == "__main__":
    asyncio.run(test_storage_manager())