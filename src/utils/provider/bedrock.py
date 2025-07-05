"""
Amazon Bedrock provider implementation with multi-model support.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception
    ProfileNotFound = Exception
    Config = None

from .base import (
    BaseProvider, ProviderConfig, Message, ChatResponse, StreamChunk,
    ModelInfo, ProviderError, ProviderTimeoutError, ProviderModelNotFoundError,
    ProviderAuthenticationError, ProviderRateLimitError, MessageRole
)

logger = logging.getLogger(__name__)


class BedrockProvider(BaseProvider):
    """Amazon Bedrock provider implementation supporting multiple model families."""
    
    # Model family detection patterns
    MODEL_FAMILIES = {
        "anthropic": [
            "anthropic.claude",
            "us.anthropic.claude"  # Inference profile format
        ],
        "llama": [
            "meta.llama",
            "us.meta.llama"  # Inference profile format
        ],
        "titan": [
            "amazon.titan"
        ],
        "jurassic": [
            "ai21.j2"
        ],
        "command": [
            "cohere.command"
        ]
    }
    
    def __init__(self, config: ProviderConfig):
        """Initialize Bedrock provider."""
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 package not installed. Please install it with: pip install boto3"
            )
        
        super().__init__(config)
        
        # AWS configuration
        self.region_name = config.config.get("region_name", "us-east-1")
        self.aws_access_key_id = os.getenv(config.config.get("access_key_env_var", "AWS_ACCESS_KEY_ID"))
        self.aws_secret_access_key = os.getenv(config.config.get("secret_key_env_var", "AWS_SECRET_ACCESS_KEY"))
        self.aws_session_token = os.getenv(config.config.get("session_token_env_var", "AWS_SESSION_TOKEN"))
        self.aws_profile = config.config.get("aws_profile")
        
        # Bedrock specific config
        self.timeout = config.config.get("timeout", 60)
        self.max_retries = config.config.get("max_retries", 3)
        
        # Client configuration
        self.client_config = Config(
            read_timeout=self.timeout,
            retries={'max_attempts': self.max_retries}
        )
        
        self.client = None
    
    async def _initialize(self):
        """Initialize Bedrock client."""
        try:
            # Set up session parameters
            session_kwargs = {}
            
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile
            elif self.aws_access_key_id and self.aws_secret_access_key:
                session_kwargs.update({
                    'aws_access_key_id': self.aws_access_key_id,
                    'aws_secret_access_key': self.aws_secret_access_key
                })
                if self.aws_session_token:
                    session_kwargs['aws_session_token'] = self.aws_session_token
            
            # Create session
            if session_kwargs:
                session = boto3.Session(**session_kwargs)
                self.client = session.client(
                    'bedrock-runtime',
                    region_name=self.region_name,
                    config=self.client_config
                )
            else:
                # Use default credentials
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region_name,
                    config=self.client_config
                )
            
            logger.info(f"Initialized Bedrock client for region {self.region_name}")
            
        except (NoCredentialsError, ProfileNotFound) as e:
            raise ProviderAuthenticationError(
                f"AWS credentials not found or invalid: {str(e)}",
                provider=self.name
            )
        except Exception as e:
            raise ProviderError(
                f"Failed to initialize Bedrock client: {str(e)}",
                provider=self.name
            )
    
    def _reinitialize_client(self):
        """Reinitialize client (synchronous version)."""
        try:
            # Set up session parameters
            session_kwargs = {}
            
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile
            elif self.aws_access_key_id and self.aws_secret_access_key:
                session_kwargs.update({
                    'aws_access_key_id': self.aws_access_key_id,
                    'aws_secret_access_key': self.aws_secret_access_key
                })
                if self.aws_session_token:
                    session_kwargs['aws_session_token'] = self.aws_session_token
            
            # Create session
            if session_kwargs:
                session = boto3.Session(**session_kwargs)
                self.client = session.client(
                    'bedrock-runtime',
                    region_name=self.region_name,
                    config=self.client_config
                )
            else:
                # Use default credentials
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region_name,
                    config=self.client_config
                )
            
        except Exception as e:
            raise ProviderError(
                f"Failed to reinitialize Bedrock client: {str(e)}",
                provider=self.name
            )
    
    async def validate_config(self) -> bool:
        """Validate Bedrock configuration by making a test API call."""
        try:
            if not self.client:
                await self.initialize()
            
            # Use the cheapest Claude model for validation
            test_model = "anthropic.claude-3-haiku-20240307-v1:0"
            
            response = self.client.converse(
                modelId=test_model,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": "Hi"}]
                    }
                ],
                inferenceConfig={
                    "maxTokens": 1,
                    "temperature": 0
                }
            )
            
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code in ['UnauthorizedOperation', 'AccessDenied', 'InvalidSignature']:
                raise ProviderAuthenticationError(
                    f"AWS authentication failed: {str(e)}",
                    provider=self.name
                )
            elif error_code == 'ValidationException':
                if 'model' in str(e).lower():
                    # Model not available in region, but auth is working
                    return True
                raise ProviderError(
                    f"Invalid Bedrock configuration: {str(e)}",
                    provider=self.name
                )
            else:
                raise ProviderError(
                    f"Failed to validate Bedrock configuration: {str(e)}",
                    provider=self.name
                )
        except Exception as e:
            raise ProviderError(
                f"Unexpected error validating Bedrock: {str(e)}",
                provider=self.name
            )
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Bedrock models from database."""
        from utils.database import SessionLocal
        from utils.repository.provider_repository import ProviderRepository
        
        db = SessionLocal()
        try:
            repo = ProviderRepository(db)
            provider_config = repo.get_by_name("bedrock")
            
            if not provider_config:
                return []
            
            models = []
            for db_model in provider_config.models:
                if db_model.is_active:
                    model_info = ModelInfo(
                        model_name=db_model.model_name,
                        display_name=db_model.display_name,
                        description=db_model.description,
                        context_window=db_model.context_window,
                        max_tokens=db_model.max_tokens,
                        supports_streaming=db_model.supports_streaming,
                        supports_functions=db_model.supports_functions,
                        capabilities=db_model.capabilities or {}
                    )
                    models.append(model_info)
            
            return models
        finally:
            db.close()
    
    def _detect_model_family(self, model: str) -> str:
        """Detect the model family from model ID."""
        model_lower = model.lower()
        
        for family, patterns in self.MODEL_FAMILIES.items():
            for pattern in patterns:
                if pattern in model_lower:
                    return family
        
        # Default to anthropic if unknown (most common)
        return "anthropic"
    
    def _prepare_messages_for_bedrock(self, messages: List[Message]) -> tuple[Optional[List[Dict[str, str]]], List[Dict[str, Any]]]:
        """
        Prepare messages for Bedrock Converse API.
        
        Returns:
            Tuple of (system_messages, user_assistant_messages)
        """
        system_messages = []
        converse_messages = []
        
        for i, msg in enumerate(messages):
            # Handle both string and enum roles
            role_value = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            
            logger.debug(f"Processing message {i}: role={role_value}, content_preview={str(msg.content)[:100]}...")
            
            if msg.role == MessageRole.SYSTEM or role_value == "system":
                # Bedrock uses separate system parameter
                system_messages.append({"text": msg.content})
            else:
                # Handle structured content (JSON) vs plain text
                content = msg.content
                
                if isinstance(content, str):
                    try:
                        # Try to parse as structured content
                        parsed_content = json.loads(content)
                        
                        # Handle different provider formats
                        if isinstance(parsed_content, list):
                            # Check if this is already in Bedrock format (toolResult/toolUse blocks)
                            if all(isinstance(item, dict) and any(key in item for key in ["toolResult", "toolUse", "text"]) for item in parsed_content):
                                # Already in Bedrock format, use as-is
                                content = parsed_content
                            else:
                                # Anthropic-style content blocks or tool results
                                content_blocks = []
                                for item in parsed_content:
                                    if item.get("type") == "text":
                                        content_blocks.append({"text": item["text"]})
                                    elif item.get("type") == "tool_use":
                                        # Convert Anthropic tool_use to Bedrock toolUse
                                        content_blocks.append({
                                            "toolUse": {
                                                "toolUseId": item["id"],
                                                "name": item["name"],
                                                "input": item["input"]
                                            }
                                        })
                                    elif item.get("type") == "tool_result":
                                        # Convert Anthropic tool_result to Bedrock toolResult
                                        content_blocks.append({
                                            "toolResult": {
                                                "toolUseId": item["tool_use_id"],
                                                "content": [{"text": str(item["content"])}],
                                                "status": "error" if item.get("is_error") else "success"
                                            }
                                        })
                                content = content_blocks
                        elif isinstance(parsed_content, dict):
                            # Handle other provider formats (OpenAI, etc.)
                            if "tool_calls" in parsed_content:
                                content_blocks = []
                                if parsed_content.get("content"):
                                    content_blocks.append({"text": parsed_content["content"]})
                                
                                # Convert tool calls
                                for tool_call in parsed_content["tool_calls"]:
                                    if "function" in tool_call:
                                        func = tool_call["function"]
                                        try:
                                            arguments = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                                        except json.JSONDecodeError:
                                            arguments = {}
                                        
                                        content_blocks.append({
                                            "toolUse": {
                                                "toolUseId": tool_call.get("id", "unknown"),
                                                "name": func["name"],
                                                "input": arguments
                                            }
                                        })
                                content = content_blocks
                            elif "tool_call_id" in parsed_content:
                                # OpenAI tool result format
                                content = [{
                                    "toolResult": {
                                        "toolUseId": parsed_content["tool_call_id"],
                                        "content": [{"text": parsed_content["content"]}],
                                        "status": "success"
                                    }
                                }]
                            elif "role" in parsed_content:
                                # Nested role message, extract content
                                content = parsed_content.get("content", str(parsed_content))
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON or not structured content, use as-is
                        pass
                
                # Ensure content is in the right format
                if isinstance(content, str):
                    # Handle empty strings - Bedrock requires non-empty text blocks
                    if content.strip():
                        content = [{"text": content}]
                    else:
                        # For empty strings, skip this message entirely
                        logger.debug(f"Skipping empty message at index {i}")
                        continue
                elif not isinstance(content, list):
                    content = [{"text": str(content)}]
                
                # Validate that content has at least one item
                if not content or len(content) == 0:
                    logger.debug(f"Skipping message with empty content at index {i}")
                    continue
                
                # Convert to Bedrock message format
                logger.debug(f"Final content for message {i}: {content}")
                converse_messages.append({
                    "role": role_value,
                    "content": content
                })
        
        return system_messages if system_messages else None, converse_messages
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Create a chat completion using Bedrock Converse API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            system_messages, converse_messages = self._prepare_messages_for_bedrock(messages)
            
            # Set default max_tokens based on model family
            if max_tokens is None:
                model_family = self._detect_model_family(model)
                if model_family == "anthropic":
                    if "haiku" in model.lower():
                        max_tokens = 4096
                    elif "opus-4" in model or "sonnet-4" in model:
                        max_tokens = 32000
                    else:
                        max_tokens = 8192
                elif model_family == "llama":
                    # Llama models typically have smaller context windows
                    if "70b" in model.lower() or "405b" in model.lower():
                        max_tokens = 8192  # Larger Llama models
                    else:
                        max_tokens = 4096  # Smaller Llama models
                else:
                    max_tokens = 4096
            
            # Build request parameters
            request_params = {
                "modelId": model,
                "messages": converse_messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                }
            }
            
            # Add system messages if present
            if system_messages:
                request_params["system"] = system_messages
            
            # Add tools if provided
            if "tools" in kwargs and kwargs["tools"]:
                bedrock_tools = self._convert_tools_to_bedrock_format(kwargs["tools"])
                request_params["toolConfig"] = {
                    "tools": bedrock_tools
                }
            
            # Add additional inference parameters
            if "top_p" in kwargs:
                request_params["inferenceConfig"]["topP"] = kwargs["top_p"]
            if "stop_sequences" in kwargs:
                request_params["inferenceConfig"]["stopSequences"] = kwargs["stop_sequences"]
            
            # Make the API call
            response = self.client.converse(**request_params)
            
            # Extract content and tool calls
            content = ""
            tool_calls = []
            
            output = response.get("output", {})
            message = output.get("message", {})
            message_content = message.get("content", [])
            
            for content_block in message_content:
                if "text" in content_block:
                    content += content_block["text"]
                elif "toolUse" in content_block:
                    tool_use = content_block["toolUse"]
                    # Convert Bedrock toolUse to standard format
                    tool_calls.append({
                        "id": tool_use.get("toolUseId", "unknown"),
                        "type": "function",
                        "function": {
                            "name": tool_use.get("name", "unknown"),
                            "arguments": json.dumps(tool_use.get("input", {}))
                        }
                    })
            
            # Get stop reason
            stop_reason = response.get("stopReason", "stop")
            
            # Get usage information
            usage_info = response.get("usage", {})
            usage = None
            if usage_info:
                usage = {
                    "prompt_tokens": usage_info.get("inputTokens", 0),
                    "completion_tokens": usage_info.get("outputTokens", 0),
                    "total_tokens": usage_info.get("totalTokens", 0)
                }
            
            return ChatResponse(
                id=f"bedrock-{datetime.now().timestamp()}",
                model=model,
                content=content,
                role="assistant",
                finish_reason=stop_reason,
                usage=usage,
                tool_calls=tool_calls if tool_calls else None
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                raise ProviderAuthenticationError(
                    "AWS authentication failed",
                    provider=self.name,
                    status_code=403
                )
            elif error_code == 'ThrottlingException':
                raise ProviderRateLimitError(
                    "Rate limit exceeded",
                    provider=self.name,
                    status_code=429
                )
            elif error_code == 'ValidationException':
                if "model" in str(e).lower():
                    raise ProviderModelNotFoundError(
                        f"Model '{model}' not found or not available in region {self.region_name}",
                        provider=self.name,
                        status_code=404
                    )
                raise ProviderError(
                    f"Invalid request: {str(e)}",
                    provider=self.name,
                    status_code=400
                )
            else:
                raise ProviderError(
                    f"Bedrock API error: {str(e)}",
                    provider=self.name,
                    status_code=getattr(e.response.get('ResponseMetadata', {}), 'HTTPStatusCode', 500)
                )
        except Exception as e:
            await self._handle_error(e, self.name)
            raise
    
    def _convert_tools_to_bedrock_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style tools to Bedrock toolSpec format."""
        bedrock_tools = []
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                bedrock_tools.append({
                    "toolSpec": {
                        "name": func["name"],
                        "description": func.get("description", f"Execute {func['name']}"),
                        "inputSchema": {
                            "json": func.get("parameters", {})
                        }
                    }
                })
        
        return bedrock_tools
    
    async def chat_completion_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Create a streaming chat completion using Bedrock Converse Stream API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            system_messages, converse_messages = self._prepare_messages_for_bedrock(messages)
            
            # Set default max_tokens based on model family
            if max_tokens is None:
                model_family = self._detect_model_family(model)
                if model_family == "anthropic":
                    if "haiku" in model.lower():
                        max_tokens = 4096
                    elif "opus-4" in model or "sonnet-4" in model:
                        max_tokens = 32000
                    else:
                        max_tokens = 8192
                elif model_family == "llama":
                    # Llama models typically have smaller context windows
                    if "70b" in model.lower() or "405b" in model.lower():
                        max_tokens = 8192  # Larger Llama models
                    else:
                        max_tokens = 4096  # Smaller Llama models
                else:
                    max_tokens = 4096
            
            # Build request parameters
            request_params = {
                "modelId": model,
                "messages": converse_messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                }
            }
            
            # Add system messages if present
            if system_messages:
                request_params["system"] = system_messages
            
            # Add tools if provided
            if "tools" in kwargs and kwargs["tools"]:
                bedrock_tools = self._convert_tools_to_bedrock_format(kwargs["tools"])
                request_params["toolConfig"] = {
                    "tools": bedrock_tools
                }
            
            # Add additional inference parameters
            if "top_p" in kwargs:
                request_params["inferenceConfig"]["topP"] = kwargs["top_p"]
            if "stop_sequences" in kwargs:
                request_params["inferenceConfig"]["stopSequences"] = kwargs["stop_sequences"]
            
            # Make the streaming API call
            response = self.client.converse_stream(**request_params)
            
            # Process streaming response
            accumulated_content = ""
            tool_calls = []
            
            for event in response.get('stream', []):
                if 'contentBlockStart' in event:
                    # Start of a content block
                    pass
                elif 'contentBlockDelta' in event:
                    # Content delta
                    delta = event['contentBlockDelta']['delta']
                    if 'text' in delta:
                        text_chunk = delta['text']
                        accumulated_content += text_chunk
                        yield StreamChunk(
                            content=text_chunk,
                            is_final=False
                        )
                elif 'contentBlockStop' in event:
                    # End of content block
                    pass
                elif 'messageStart' in event:
                    # Start of message
                    pass
                elif 'messageStop' in event:
                    # End of message - final chunk
                    stop_reason = event['messageStop'].get('stopReason', 'stop')
                    
                    # Check for tool usage in the message
                    output = event.get('messageStop', {}).get('message', {})
                    if 'content' in output:
                        for content_block in output['content']:
                            if 'toolUse' in content_block:
                                tool_use = content_block['toolUse']
                                tool_calls.append({
                                    "id": tool_use.get("toolUseId", "unknown"),
                                    "type": "function",
                                    "function": {
                                        "name": tool_use.get("name", "unknown"),
                                        "arguments": json.dumps(tool_use.get("input", {}))
                                    }
                                })
                    
                    yield StreamChunk(
                        content="",
                        is_final=True,
                        finish_reason=stop_reason
                    )
                elif 'metadata' in event:
                    # Usage information
                    usage_info = event['metadata'].get('usage', {})
                    if usage_info:
                        yield StreamChunk(
                            content="",
                            is_final=True,
                            usage={
                                "prompt_tokens": usage_info.get("inputTokens", 0),
                                "completion_tokens": usage_info.get("outputTokens", 0),
                                "total_tokens": usage_info.get("totalTokens", 0)
                            }
                        )
                    
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code in ['UnauthorizedOperation', 'AccessDenied']:
                raise ProviderAuthenticationError(
                    "AWS authentication failed",
                    provider=self.name,
                    status_code=403
                )
            elif error_code == 'ThrottlingException':
                raise ProviderRateLimitError(
                    "Rate limit exceeded",
                    provider=self.name,
                    status_code=429
                )
            elif error_code == 'ValidationException':
                if "model" in str(e).lower():
                    raise ProviderModelNotFoundError(
                        f"Model '{model}' not found or not available in region {self.region_name}",
                        provider=self.name,
                        status_code=404
                    )
                raise ProviderError(
                    f"Invalid request: {str(e)}",
                    provider=self.name,
                    status_code=400
                )
            else:
                raise ProviderError(
                    f"Bedrock API error: {str(e)}",
                    provider=self.name,
                    status_code=getattr(e.response.get('ResponseMetadata', {}), 'HTTPStatusCode', 500)
                )
        except Exception as e:
            await self._handle_error(e, self.name)
            raise