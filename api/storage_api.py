"""
API Integration for Cloud Storage and Plugin Distribution

FastAPI routes and endpoints for:
- File uploads and downloads
- Plugin marketplace
- User data management
- Plugin distribution
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
import json
import logging
from datetime import datetime
import asyncio

# Import our storage and distribution systems
from .cloud_storage import CloudStorageManager, create_storage_manager
from .plugin_distribution import PluginDistributionManager, PluginMarketplace, create_plugin_distribution_manager

# Pydantic models for API
class FileUploadResponse(BaseModel):
    """File upload response"""
    success: bool
    file_key: str
    file_size: int
    content_type: str
    upload_time: str
    download_url: Optional[str] = None

class PluginSearchRequest(BaseModel):
    """Plugin search request"""
    query: str
    category: Optional[str] = None
    limit: int = 20

class PluginDownloadRequest(BaseModel):
    """Plugin download request"""
    plugin_id: str
    version: str

class PluginDownloadResponse(BaseModel):
    """Plugin download response"""
    download_id: str
    status: str
    estimated_time: Optional[int] = None

class UserDataExportRequest(BaseModel):
    """User data export request"""
    format: str = "json"  # json, csv
    include_workouts: bool = True
    include_progress: bool = True
    date_range_days: Optional[int] = None

# Global managers (will be initialized on startup)
storage_manager: Optional[CloudStorageManager] = None
distribution_manager: Optional[PluginDistributionManager] = None
marketplace: Optional[PluginMarketplace] = None

# API Router
router = APIRouter(prefix="/api/storage", tags=["Cloud Storage"])
plugin_router = APIRouter(prefix="/api/plugins", tags=["Plugin Marketplace"])

async def get_storage_manager() -> CloudStorageManager:
    """Dependency to get storage manager"""
    global storage_manager
    if storage_manager is None:
        storage_manager = create_storage_manager()
        await storage_manager.initialize()
    return storage_manager

async def get_distribution_manager() -> PluginDistributionManager:
    """Dependency to get distribution manager"""
    global distribution_manager
    if distribution_manager is None:
        storage = await get_storage_manager()
        distribution_manager = create_plugin_distribution_manager(storage)
    return distribution_manager

async def get_marketplace() -> PluginMarketplace:
    """Dependency to get marketplace"""
    global marketplace
    if marketplace is None:
        dist_manager = await get_distribution_manager()
        marketplace = PluginMarketplace(dist_manager)
    return marketplace

# File upload/download endpoints
@router.post("/upload/{user_id}", response_model=FileUploadResponse)
async def upload_user_file(
    user_id: str,
    file: UploadFile = File(...),
    folder: str = "uploads",
    storage: CloudStorageManager = Depends(get_storage_manager)
):
    """Upload file for a user"""
    try:
        # Read file data
        file_data = await file.read()
        
        # Generate storage key
        if folder == "uploads":
            storage_key = storage.get_user_upload_path(user_id, file.filename)
        elif folder == "data":
            storage_key = storage.get_user_data_path(user_id, file.filename)
        else:
            storage_key = f"users/{user_id}/{folder}/{file.filename}"
        
        # Upload file
        success = await storage.upload_file(
            file_data,
            storage_key,
            file.content_type,
            metadata={
                "original_filename": file.filename,
                "user_id": user_id,
                "folder": folder
            }
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="File upload failed")
        
        # Generate download URL
        download_url = await storage.generate_presigned_url(storage_key)
        
        return FileUploadResponse(
            success=True,
            file_key=storage_key,
            file_size=len(file_data),
            content_type=file.content_type or "application/octet-stream",
            upload_time=datetime.now().isoformat(),
            download_url=download_url
        )
        
    except Exception as e:
        logging.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{user_id}/{file_key:path}")
async def download_user_file(
    user_id: str,
    file_key: str,
    storage: CloudStorageManager = Depends(get_storage_manager)
):
    """Download file for a user"""
    try:
        # Validate that file belongs to user
        if not file_key.startswith(f"users/{user_id}/"):
            file_key = f"users/{user_id}/{file_key}"
        
        # Get file data
        file_data = await storage.download_file(file_key)
        
        if file_data is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get file info for metadata
        file_info = await storage.get_file_info(file_key)
        
        # Return file as streaming response
        def generate():
            yield file_data
        
        return StreamingResponse(
            generate(),
            media_type=file_info.content_type if file_info else "application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(file_key)}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"File download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/{user_id}")
async def list_user_files(
    user_id: str,
    folder: str = "uploads",
    storage: CloudStorageManager = Depends(get_storage_manager)
):
    """List files for a user"""
    try:
        # Create prefix for user files
        if folder == "uploads":
            prefix = f"users/{user_id}/uploads/"
        elif folder == "data":
            prefix = f"users/{user_id}/data/"
        else:
            prefix = f"users/{user_id}/{folder}/"
        
        # List files
        files = await storage.list_files(prefix)
        
        # Format response
        file_list = []
        for file_obj in files:
            file_list.append({
                "key": file_obj.key,
                "filename": os.path.basename(file_obj.key),
                "size": file_obj.size,
                "content_type": file_obj.content_type,
                "last_modified": file_obj.last_modified.isoformat(),
                "download_url": f"/api/storage/download/{user_id}/{file_obj.key.replace(f'users/{user_id}/', '')}"
            })
        
        return {
            "user_id": user_id,
            "folder": folder,
            "files": file_list,
            "total_files": len(file_list)
        }
        
    except Exception as e:
        logging.error(f"File listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/files/{user_id}/{file_key:path}")
async def delete_user_file(
    user_id: str,
    file_key: str,
    storage: CloudStorageManager = Depends(get_storage_manager)
):
    """Delete file for a user"""
    try:
        # Validate that file belongs to user
        if not file_key.startswith(f"users/{user_id}/"):
            file_key = f"users/{user_id}/{file_key}"
        
        # Delete file
        success = await storage.delete_file(file_key)
        
        if not success:
            raise HTTPException(status_code=404, detail="File not found or deletion failed")
        
        return {"success": True, "message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"File deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Plugin marketplace endpoints
@plugin_router.get("/featured")
async def get_featured_plugins(
    limit: int = 10,
    marketplace: PluginMarketplace = Depends(get_marketplace)
):
    """Get featured plugins"""
    try:
        featured = await marketplace.get_featured_plugins(limit)
        return {
            "featured_plugins": featured,
            "total": len(featured)
        }
    except Exception as e:
        logging.error(f"Featured plugins failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.post("/search")
async def search_plugins(
    search_request: PluginSearchRequest,
    marketplace: PluginMarketplace = Depends(get_marketplace)
):
    """Search plugins"""
    try:
        results = await marketplace.search_plugins(
            search_request.query,
            search_request.category
        )
        
        # Limit results
        limited_results = results[:search_request.limit]
        
        return {
            "query": search_request.query,
            "category": search_request.category,
            "results": limited_results,
            "total_results": len(results),
            "returned_results": len(limited_results)
        }
    except Exception as e:
        logging.error(f"Plugin search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/available")
async def get_available_plugins(
    distribution: PluginDistributionManager = Depends(get_distribution_manager)
):
    """Get all available plugins"""
    try:
        packages = await distribution.get_available_plugins()
        
        plugins = []
        for package in packages:
            plugins.append({
                "plugin_id": package.plugin_id,
                "version": package.version,
                "name": package.manifest.get("name", package.plugin_id),
                "description": package.manifest.get("description", ""),
                "price": package.manifest.get("price", 0),
                "size": package.size,
                "created_at": package.created_at,
                "updated_at": package.updated_at
            })
        
        return {
            "plugins": plugins,
            "total": len(plugins)
        }
    except Exception as e:
        logging.error(f"Get available plugins failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/{plugin_id}")
async def get_plugin_details(
    plugin_id: str,
    version: Optional[str] = None,
    distribution: PluginDistributionManager = Depends(get_distribution_manager)
):
    """Get plugin details"""
    try:
        package = await distribution.get_plugin_package(plugin_id, version)
        
        if not package:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        return {
            "plugin_id": package.plugin_id,
            "version": package.version,
            "name": package.manifest.get("name", package.plugin_id),
            "description": package.manifest.get("description", ""),
            "author": package.manifest.get("author", ""),
            "price": package.manifest.get("price", 0),
            "trial_days": package.manifest.get("trial_days", 0),
            "size": package.size,
            "dependencies": package.dependencies,
            "manifest": package.manifest,
            "created_at": package.created_at,
            "updated_at": package.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get plugin details failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.post("/download/{user_id}", response_model=PluginDownloadResponse)
async def initiate_plugin_download(
    user_id: str,
    download_request: PluginDownloadRequest,
    distribution: PluginDistributionManager = Depends(get_distribution_manager)
):
    """Initiate plugin download for user"""
    try:
        download_record = await distribution.initiate_plugin_download(
            user_id,
            download_request.plugin_id,
            download_request.version
        )
        
        if not download_record:
            raise HTTPException(status_code=404, detail="Plugin not found or download failed")
        
        return PluginDownloadResponse(
            download_id=download_record.download_id,
            status=download_record.status,
            estimated_time=30  # Mock estimated time in seconds
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Plugin download initiation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/download/status/{download_id}")
async def get_download_status(
    download_id: str,
    distribution: PluginDistributionManager = Depends(get_distribution_manager)
):
    """Get plugin download status"""
    try:
        download_record = await distribution.get_download_status(download_id)
        
        if not download_record:
            raise HTTPException(status_code=404, detail="Download record not found")
        
        return {
            "download_id": download_record.download_id,
            "status": download_record.status,
            "plugin_id": download_record.plugin_id,
            "version": download_record.version,
            "download_started": download_record.download_started,
            "download_completed": download_record.download_completed,
            "download_size": download_record.download_size,
            "error_message": download_record.error_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get download status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/user/{user_id}/plugins")
async def get_user_plugins(
    user_id: str,
    distribution: PluginDistributionManager = Depends(get_distribution_manager)
):
    """Get plugins owned by user"""
    try:
        user_plugins = await distribution.get_user_plugins(user_id)
        
        return {
            "user_id": user_id,
            "plugins": user_plugins,
            "total": len(user_plugins)
        }
    except Exception as e:
        logging.error(f"Get user plugins failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/user/{user_id}/updates")
async def check_plugin_updates(
    user_id: str,
    distribution: PluginDistributionManager = Depends(get_distribution_manager)
):
    """Check for plugin updates for user"""
    try:
        updates = await distribution.check_plugin_updates(user_id)
        
        return {
            "user_id": user_id,
            "updates_available": updates,
            "total_updates": len(updates)
        }
    except Exception as e:
        logging.error(f"Check plugin updates failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Data export endpoints
@router.post("/export/{user_id}")
async def export_user_data(
    user_id: str,
    export_request: UserDataExportRequest,
    background_tasks: BackgroundTasks,
    storage: CloudStorageManager = Depends(get_storage_manager)
):
    """Export user data"""
    try:
        # Generate export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"user_data_export_{timestamp}.{export_request.format}"
        
        # Start background export task
        background_tasks.add_task(
            _process_user_data_export,
            user_id,
            export_request,
            export_filename,
            storage
        )
        
        return {
            "message": "Data export initiated",
            "export_filename": export_filename,
            "format": export_request.format,
            "estimated_time": "5-10 minutes"
        }
    except Exception as e:
        logging.error(f"Data export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _process_user_data_export(
    user_id: str,
    export_request: UserDataExportRequest,
    export_filename: str,
    storage: CloudStorageManager
):
    """Process user data export in background"""
    try:
        # Mock export data (in real implementation, gather from database and files)
        export_data = {
            "user_id": user_id,
            "export_date": datetime.now().isoformat(),
            "format": export_request.format,
            "data": {
                "profile": {"username": f"user_{user_id}"},
                "workouts": [] if not export_request.include_workouts else [
                    {"id": "workout_1", "date": "2024-01-01", "type": "strength"}
                ],
                "progress": {} if not export_request.include_progress else {
                    "total_workouts": 50,
                    "total_volume": 10000
                }
            }
        }
        
        # Convert to bytes
        if export_request.format == "json":
            export_bytes = json.dumps(export_data, indent=2).encode()
            content_type = "application/json"
        else:
            # CSV format (simplified)
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Field", "Value"])
            writer.writerow(["User ID", user_id])
            writer.writerow(["Export Date", export_data["export_date"]])
            
            export_bytes = output.getvalue().encode()
            content_type = "text/csv"
        
        # Upload export file
        export_key = storage.get_workout_export_path(user_id, export_filename)
        
        await storage.upload_file(
            export_bytes,
            export_key,
            content_type,
            metadata={
                "export_type": "user_data",
                "export_date": datetime.now().isoformat(),
                "user_id": user_id
            }
        )
        
        logging.info(f"✅ User data export completed: {export_filename}")
        
    except Exception as e:
        logging.error(f"User data export processing failed: {e}")

# Health check endpoint
@router.get("/health")
async def storage_health_check():
    """Health check for storage services"""
    try:
        storage = await get_storage_manager()
        
        # Test basic storage operation
        test_key = "health_check/test.txt"
        test_data = b"Health check test"
        
        # Upload test file
        upload_success = await storage.upload_file(test_data, test_key, "text/plain")
        
        # Download test file
        download_data = await storage.download_file(test_key) if upload_success else None
        
        # Cleanup test file
        if upload_success:
            await storage.delete_file(test_key)
        
        return {
            "status": "healthy" if upload_success and download_data == test_data else "unhealthy",
            "provider": storage.provider.value if storage.provider else "unknown",
            "upload_test": upload_success,
            "download_test": download_data == test_data if download_data else False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Storage health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Include routers in main app
def include_storage_routes(app):
    """Include storage routes in FastAPI app"""
    app.include_router(router)
    app.include_router(plugin_router)