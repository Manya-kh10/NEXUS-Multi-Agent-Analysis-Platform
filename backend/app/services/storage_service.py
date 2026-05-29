import os
import httpx
import logging
import asyncio
from app.config import settings

logger = logging.getLogger("nexus.storage")

# Determine local storage path
LOCAL_STORAGE_DIR = "/app/data/storage" if os.path.exists("/app/data") else os.path.abspath(os.path.join(os.getcwd(), "data", "storage"))

def get_supabase_key() -> str:
    """Resolves active Supabase API key dynamically from standard config inputs."""
    return settings.supabase_service_role_key or settings.supabase_anon_key or os.getenv("SUPABASE_KEY", "")

def is_supabase_enabled() -> bool:
    return bool(settings.supabase_url and get_supabase_key())

async def initialize_storage():
    """Initializes local storage directories or verifies Supabase bucket access."""
    if is_supabase_enabled():
        logger.info("Supabase storage enabled. Verifying connection...")
        try:
            # Try to verify/create the bucket via REST API
            bucket_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/{settings.supabase_bucket}"
            headers = {"Authorization": f"Bearer {get_supabase_key()}"}
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get(bucket_url, headers=headers)
                if res.status_code == 404:
                    logger.info(f"Bucket '{settings.supabase_bucket}' not found. Attempting to create...")
                    create_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket"
                    body = {
                        "id": settings.supabase_bucket,
                        "name": settings.supabase_bucket,
                        "public": False
                    }
                    res_create = await client.post(create_url, headers=headers, json=body)
                    if res_create.status_code in [200, 201]:
                        logger.info(f"Bucket '{settings.supabase_bucket}' created successfully.")
                    else:
                        logger.warning(f"Could not create Supabase bucket: {res_create.text}")
                elif res.status_code == 200:
                    logger.info(f"Bucket '{settings.supabase_bucket}' verified.")
                else:
                    logger.warning(f"Unexpected response checking Supabase bucket: {res.status_code}")
        except Exception as e:
            logger.error(f"Error initializing Supabase storage: {e}. Falling back to local disk storage.")
            os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    else:
        logger.info(f"Local storage fallback active. Ensuring directory exists: {LOCAL_STORAGE_DIR}")
        os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

async def upload_file(filename: str, file_bytes: bytes, dataset_id: str) -> str:
    """Uploads file to active storage provider with resilient retry mechanism."""
    object_path = f"{dataset_id}/{filename}"
    
    if is_supabase_enabled():
        max_retries = 3
        backoff_sec = 1.0
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Uploading {filename} (ID: {dataset_id}) to Supabase Storage [Attempt {attempt}/{max_retries}]...")
                upload_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}/{object_path}"
                headers = {
                    "Authorization": f"Bearer {get_supabase_key()}",
                    "Content-Type": "text/csv"
                }
                async with httpx.AsyncClient(timeout=15) as client:
                    res = await client.post(upload_url, headers=headers, content=file_bytes)
                    if res.status_code in [200, 201]:
                        logger.info("Upload to Supabase Storage completed successfully.")
                        return f"supabase://{settings.supabase_bucket}/{object_path}"
                    else:
                        logger.warning(f"Supabase upload attempt {attempt} failed ({res.status_code}): {res.text}")
            except Exception as e:
                logger.warning(f"Supabase upload attempt {attempt} threw exception: {e}")
                
            if attempt < max_retries:
                sleep_duration = backoff_sec * (2 ** (attempt - 1))
                logger.info(f"Backing off for {sleep_duration} seconds before retrying...")
                await asyncio.sleep(sleep_duration)
                
        logger.error("All Supabase upload attempts exhausted. Falling back to local storage.")
            
    # Fallback to Local Storage
    logger.info(f"Uploading {filename} (ID: {dataset_id}) to Local Storage Fallback...")
    try:
        folder_path = os.path.join(LOCAL_STORAGE_DIR, dataset_id)
        os.makedirs(folder_path, exist_ok=True)
        local_file_path = os.path.join(folder_path, filename)
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)
        logger.info("Local storage upload completed successfully.")
        return f"local://{object_path}"
    except Exception as e:
        logger.error(f"Local storage fallback upload failed: {e}")
        raise e

async def download_file(storage_url: str) -> bytes:
    """Downloads and returns the file bytes from designated storage URL with resilient retry mechanism."""
    if storage_url.startswith("supabase://"):
        max_retries = 3
        backoff_sec = 1.0
        object_path = storage_url.replace(f"supabase://{settings.supabase_bucket}/", "")
        
        for attempt in range(1, max_retries + 1):
            try:
                download_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}/{object_path}"
                headers = {"Authorization": f"Bearer {get_supabase_key()}"}
                logger.info(f"Downloading file from Supabase Storage: {object_path} [Attempt {attempt}/{max_retries}]")
                async with httpx.AsyncClient(timeout=20) as client:
                    res = await client.get(download_url, headers=headers)
                    if res.status_code == 200:
                        return res.content
                    else:
                        logger.warning(f"Supabase download attempt {attempt} returned {res.status_code}: {res.text}")
            except Exception as e:
                logger.warning(f"Supabase download attempt {attempt} threw exception: {e}")
                
            if attempt < max_retries:
                sleep_duration = backoff_sec * (2 ** (attempt - 1))
                logger.info(f"Backing off for {sleep_duration} seconds before retrying...")
                await asyncio.sleep(sleep_duration)
                
        logger.error("All Supabase download attempts exhausted. Checking for local fallback...")
        # Check if local file exists as fallback
        local_path = os.path.join(LOCAL_STORAGE_DIR, object_path)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        raise Exception(f"All download attempts for Supabase storage failed: {storage_url}")

    elif storage_url.startswith("local://"):
        object_path = storage_url.replace("local://", "")
        local_path = os.path.join(LOCAL_STORAGE_DIR, object_path)
        logger.info(f"Downloading file from Local Storage: {local_path}")
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found at: {local_path}")
        with open(local_path, "rb") as f:
            return f.read()
            
    else:
        # Backward compatibility for direct folder path
        if os.path.exists(storage_url):
            logger.info(f"Downloading direct file path: {storage_url}")
            with open(storage_url, "rb") as f:
                return f.read()
        raise ValueError(f"Unknown or unsupported storage protocol in URL: {storage_url}")

async def delete_file(storage_url: str):
    """Deletes the object from active storage provider."""
    if storage_url.startswith("supabase://"):
        try:
            object_path = storage_url.replace(f"supabase://{settings.supabase_bucket}/", "")
            delete_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}"
            headers = {
                "Authorization": f"Bearer {get_supabase_key()}",
                "Content-Type": "application/json"
            }
            logger.info(f"Deleting file from Supabase Storage: {object_path}")
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.request("DELETE", delete_url, headers=headers, json={"prefixes": [object_path]})
                if res.status_code != 200:
                    logger.warning(f"Supabase delete failed: {res.text}")
        except Exception as e:
            logger.error(f"Supabase delete exception: {e}")
            
    elif storage_url.startswith("local://"):
        object_path = storage_url.replace("local://", "")
        local_path = os.path.join(LOCAL_STORAGE_DIR, object_path)
        logger.info(f"Deleting file from Local Storage: {local_path}")
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                # Cleanup parent folder if empty
                parent_dir = os.path.dirname(local_path)
                if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
            except Exception as e:
                logger.error(f"Failed to delete local file or directory: {e}")
