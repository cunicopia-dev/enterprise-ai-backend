from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any


class MCPTransport(ABC):
    """Abstract base class for MCP transports"""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the transport connection"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the transport connection"""
        pass
    
    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a message through the transport"""
        pass
    
    @abstractmethod
    async def receive(self) -> AsyncIterator[str]:
        """Receive messages from the transport"""
        pass