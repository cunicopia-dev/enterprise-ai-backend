import json
import logging
from pathlib import Path
from typing import Dict, Optional
import os

from .models import MCPServerConfig, TransportType
from .exceptions import MCPConfigurationError

logger = logging.getLogger(__name__)


class MCPConfigLoader:
    """Loads and validates MCP server configurations"""
    
    DEFAULT_CONFIG_PATH = "mcp_servers_config.json"
    
    @staticmethod
    def load_config(config_path: Optional[str] = None) -> Dict[str, MCPServerConfig]:
        """Load MCP server configurations from JSON file"""
        if config_path is None:
            # Try to find config file in project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / MCPConfigLoader.DEFAULT_CONFIG_PATH
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            logger.warning(f"MCP config file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Extract mcp_servers section
            mcp_servers_data = data.get('mcp_servers', {})
            
            # Parse and validate each server config
            configs = {}
            for server_name, server_data in mcp_servers_data.items():
                try:
                    # Validate transport type
                    transport_type = server_data.get('transport_type', 'stdio')
                    if transport_type not in [t.value for t in TransportType]:
                        raise MCPConfigurationError(
                            f"Invalid transport type for {server_name}: {transport_type}"
                        )
                    
                    # Create config object
                    # Handle both 'enabled' and 'is_active' for backward compatibility
                    enabled = server_data.get('enabled', server_data.get('is_active', True))
                    
                    config = MCPServerConfig(
                        transport_type=TransportType(transport_type),
                        config=server_data.get('config', {}),
                        env=server_data.get('env', {}),
                        enabled=enabled
                    )
                    
                    configs[server_name] = config
                    logger.info(f"Loaded config for MCP server: {server_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to parse config for {server_name}: {e}")
                    continue
            
            return configs
            
        except json.JSONDecodeError as e:
            raise MCPConfigurationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise MCPConfigurationError(f"Failed to load config: {e}")
    
    @staticmethod
    def validate_stdio_config(config: Dict) -> bool:
        """Validate stdio transport configuration"""
        if 'command' not in config:
            return False
        
        # Check if command exists
        command = config['command']
        if not MCPConfigLoader._command_exists(command):
            logger.warning(f"Command not found: {command}")
        
        return True
    
    @staticmethod
    def validate_sse_config(config: Dict) -> bool:
        """Validate SSE transport configuration"""
        if 'url' not in config:
            return False
        
        # Basic URL validation could be added here
        return True
    
    @staticmethod
    def _command_exists(command: str) -> bool:
        """Check if a command exists in PATH"""
        from shutil import which
        return which(command) is not None
    
    @staticmethod
    def get_config_with_overrides(
        base_config: Dict[str, MCPServerConfig],
        overrides: Optional[Dict[str, Dict]] = None
    ) -> Dict[str, MCPServerConfig]:
        """Apply runtime overrides to base configuration"""
        if not overrides:
            return base_config
        
        # Create a copy to avoid modifying original
        config = base_config.copy()
        
        for server_name, override_data in overrides.items():
            if server_name in config:
                # Update existing config
                if 'enabled' in override_data:
                    config[server_name].enabled = override_data['enabled']
                if 'env' in override_data:
                    config[server_name].env.update(override_data['env'])
            else:
                # Add new server config
                try:
                    config[server_name] = MCPServerConfig(**override_data)
                except Exception as e:
                    logger.error(f"Invalid override config for {server_name}: {e}")
        
        return config