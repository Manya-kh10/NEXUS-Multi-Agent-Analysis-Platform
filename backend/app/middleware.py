from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nexus")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        url = request.url.path

        try:
            response = await call_next(request)
            duration = round((time.time() - start_time) * 1000, 2)
            logger.info(f"{method} {url} - {response.status_code} - {duration}ms")
            return response
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(f"{method} {url} - ERROR - {duration}ms - {str(e)}")
            raise

class FileSizeMiddleware(BaseHTTPMiddleware):
    MAX_SIZE = 50 * 1024 * 1024  # 50MB

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="File too large. Maximum size is 50MB."
                )
        return await call_next(request)