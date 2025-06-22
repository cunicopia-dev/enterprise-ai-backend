import asyncio
import json
import logging
import os
from typing import AsyncIterator, Optional, Dict, Any

from . import MCPTransport
from ..exceptions import MCPTransportError

logger = logging.getLogger(__name__)


class StdioTransport(MCPTransport):
    """Stdio transport for MCP - communicates with subprocess via stdin/stdout"""
    
    def __init__(self, config: Dict[str, Any], env: Optional[Dict[str, str]] = None):
        self.command = config.get('command')
        self.args = config.get('args', [])
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None
        self._closed = False
        
    async def start(self) -> None:
        """Start the subprocess"""
        if self.process is not None:
            raise MCPTransportError("Transport already started")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(self.env)
        
        # Start subprocess
        try:
            cmd = [self.command] + self.args
            logger.debug(f"Starting subprocess: {' '.join(cmd)}")
            
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Start stderr logger
            asyncio.create_task(self._log_stderr())
            
            logger.info(f"Started subprocess: {self.command}")
            
        except Exception as e:
            raise MCPTransportError(f"Failed to start subprocess: {e}")
    
    async def close(self) -> None:
        """Close the subprocess"""
        self._closed = True
        
        if self.process:
            try:
                # Try graceful shutdown
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if not responding
                    self.process.kill()
                    await self.process.wait()
                    
                logger.info("Subprocess terminated")
                
            except Exception as e:
                logger.error(f"Error closing subprocess: {e}")
            finally:
                self.process = None
    
    async def send(self, message: str) -> None:
        """Send a message to the subprocess"""
        if not self.process or self.process.stdin is None:
            raise MCPTransportError("Transport not connected")
        
        try:
            # MCP uses line-delimited JSON
            data = message.encode('utf-8') + b'\n'
            self.process.stdin.write(data)
            await self.process.stdin.drain()
            
            logger.info(f"SENT: {message}")
            
        except Exception as e:
            raise MCPTransportError(f"Failed to send message: {e}")
    
    async def receive(self) -> AsyncIterator[str]:
        """Receive messages from the subprocess"""
        if not self.process or self.process.stdout is None:
            raise MCPTransportError("Transport not connected")
        
        while not self._closed and self.process.stdout:
            try:
                # Read line from stdout
                line = await self.process.stdout.readline()
                
                if not line:
                    # Process ended
                    break
                
                # Decode and strip newline
                message = line.decode('utf-8').strip()
                
                if message:
                    logger.info(f"RECV: {message}")
                    yield message
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                if not self._closed:
                    raise MCPTransportError(f"Failed to receive message: {e}")
    
    async def _log_stderr(self) -> None:
        """Log stderr output from subprocess"""
        if not self.process or self.process.stderr is None:
            return
        
        try:
            while not self._closed and self.process.stderr:
                line = await self.process.stderr.readline()
                if not line:
                    break
                
                error_msg = line.decode('utf-8').strip()
                if error_msg:
                    logger.info(f"STDERR: {error_msg}")
                    
        except Exception as e:
            logger.error(f"Error reading stderr: {e}")