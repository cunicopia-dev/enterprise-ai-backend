class MCPException(Exception):
    """Base exception for all MCP-related errors"""
    pass


class MCPConnectionError(MCPException):
    """Raised when connection to MCP server fails"""
    pass


class MCPTransportError(MCPException):
    """Raised when transport-level errors occur"""
    pass


class MCPProtocolError(MCPException):
    """Raised when protocol violations occur"""
    pass


class MCPServerError(MCPException):
    """Raised when MCP server returns an error"""
    def __init__(self, code: int, message: str, data: dict = None):
        self.code = code
        self.data = data
        super().__init__(message)


class MCPTimeoutError(MCPException):
    """Raised when MCP operations timeout"""
    pass


class MCPConfigurationError(MCPException):
    """Raised when MCP configuration is invalid"""
    pass


class MCPToolExecutionError(MCPException):
    """Raised when tool execution fails"""
    pass