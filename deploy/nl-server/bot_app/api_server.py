"""
FastAPI server runner for subscription API
Runs alongside Telegram bot in same process
"""

import logging
import asyncio
import uvicorn
from typing import Optional

logger = logging.getLogger(__name__)


class APIServer:
    """FastAPI server manager"""

    def __init__(self, app, host: str = "0.0.0.0", port: int = 8000):
        """
        Initialize API server

        Args:
            app: FastAPI application instance
            host: Host to bind to
            port: Port to listen on
        """
        self.app = app
        self.host = host
        self.port = port
        self.server: Optional[uvicorn.Server] = None

    async def start(self):
        """Start FastAPI server"""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,  # Disable access logs to reduce noise
        )
        self.server = uvicorn.Server(config)

        logger.info(f"Starting Subscription API on {self.host}:{self.port}")

        # Run server
        await self.server.serve()

    async def stop(self):
        """Stop FastAPI server"""
        if self.server:
            logger.info("Stopping Subscription API")
            self.server.should_exit = True
