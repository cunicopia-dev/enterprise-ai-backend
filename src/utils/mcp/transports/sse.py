import asyncio
import json
import logging
from typing import AsyncIterator, Optional, Dict, Any
import aiohttp
from aiohttp_sse_client import client as sse_client

from . import MCPTransport
from ..exceptions import MCPTransportError

logger = logging.getLogger(__name__)


class SSETransport(MCPTransport):
    """Server-Sent Events transport for MCP"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get('url')
        self.headers = config.get('headers', {})
        self.session: Optional[aiohttp.ClientSession] = None
        self.event_source: Optional[sse_client.EventSource] = None
        self._send_url: Optional[str] = None
        self._closed = False
        
        if not self.url:
            raise MCPTransportError("SSE transport requires 'url' in config")
        
        # Determine send URL (might be different from SSE endpoint)
        self._send_url = config.get('send_url', self.url.replace('/events', '/messages'))
    
    async def start(self) -> None:
        """Start the SSE connection"""
        if self.session is not None:
            raise MCPTransportError("Transport already started")
        
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession(headers=self.headers)
            
            # Connect to SSE endpoint
            self.event_source = sse_client.EventSource(
                self.url,
                session=self.session,
                headers=self.headers
            )
            
            logger.info(f"Connected to SSE endpoint: {self.url}")
            
        except Exception as e:
            await self.close()
            raise MCPTransportError(f"Failed to connect to SSE endpoint: {e}")
    
    async def close(self) -> None:
        """Close the SSE connection"""
        self._closed = True
        
        if self.event_source:
            await self.event_source.close()
            self.event_source = None
        
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("SSE connection closed")
    
    async def send(self, message: str) -> None:
        """Send a message via HTTP POST"""
        if not self.session:
            raise MCPTransportError("Transport not connected")
        
        try:
            # Send message as JSON via POST
            async with self.session.post(
                self._send_url,
                json=json.loads(message),
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status not in (200, 201, 204):
                    text = await response.text()
                    raise MCPTransportError(
                        f"Failed to send message: {response.status} - {text}"
                    )
            
            logger.debug(f"Sent message via POST to {self._send_url}")
            
        except aiohttp.ClientError as e:
            raise MCPTransportError(f"HTTP error sending message: {e}")
        except Exception as e:
            raise MCPTransportError(f"Failed to send message: {e}")
    
    async def receive(self) -> AsyncIterator[str]:
        """Receive messages from SSE stream"""
        if not self.event_source:
            raise MCPTransportError("Transport not connected")
        
        try:
            async for event in self.event_source:
                if self._closed:
                    break
                
                # SSE events have data field
                if event.data:
                    logger.debug(f"Received SSE event: {event.data}")
                    yield event.data
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._closed:
                logger.error(f"Error receiving SSE event: {e}")
                raise MCPTransportError(f"Failed to receive message: {e}")