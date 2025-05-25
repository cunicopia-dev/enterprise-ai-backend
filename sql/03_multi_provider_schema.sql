-- Migration for multi-provider support
-- This adds support for multiple AI providers (Ollama, Anthropic, OpenAI, etc.)

-- Create provider_configs table to store provider configurations
CREATE TABLE IF NOT EXISTS provider_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(50) NOT NULL CHECK (provider_type IN ('ollama', 'anthropic', 'openai', 'google', 'custom')),
    base_url VARCHAR(500),
    api_key_env_var VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create provider_models table to store available models per provider
CREATE TABLE IF NOT EXISTS provider_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES provider_configs(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    capabilities JSONB DEFAULT '{}',
    context_window INTEGER,
    max_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT TRUE,
    supports_functions BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (provider_id, model_name)
);

-- Create provider_usage table to track usage per provider/model
CREATE TABLE IF NOT EXISTS provider_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider_id UUID REFERENCES provider_configs(id) ON DELETE SET NULL,
    model_id UUID REFERENCES provider_models(id) ON DELETE SET NULL,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    tokens_total INTEGER DEFAULT 0,
    cost_input DECIMAL(10, 6) DEFAULT 0,
    cost_output DECIMAL(10, 6) DEFAULT 0,
    cost_total DECIMAL(10, 6) DEFAULT 0,
    latency_ms INTEGER,
    status VARCHAR(50) DEFAULT 'success' CHECK (status IN ('success', 'error', 'timeout', 'cancelled')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add provider and model columns to chats table
ALTER TABLE chats 
ADD COLUMN IF NOT EXISTS provider_id UUID REFERENCES provider_configs(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS model_id UUID REFERENCES provider_models(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS temperature DECIMAL(3, 2) DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
ADD COLUMN IF NOT EXISTS max_tokens INTEGER;

-- Add provider and model columns to messages table for tracking
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS provider_id UUID REFERENCES provider_configs(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS model_id UUID REFERENCES provider_models(id) ON DELETE SET NULL;

-- Add is_default column to system_prompts table if it doesn't exist
ALTER TABLE system_prompts 
ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE;

-- Create triggers for updated_at on new tables
CREATE TRIGGER update_provider_configs_updated_at
BEFORE UPDATE ON provider_configs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_provider_models_updated_at
BEFORE UPDATE ON provider_models
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_provider_models_provider_id ON provider_models(provider_id);
CREATE INDEX IF NOT EXISTS idx_provider_usage_user_id ON provider_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_provider_usage_provider_id ON provider_usage(provider_id);
CREATE INDEX IF NOT EXISTS idx_provider_usage_model_id ON provider_usage(model_id);
CREATE INDEX IF NOT EXISTS idx_provider_usage_chat_id ON provider_usage(chat_id);
CREATE INDEX IF NOT EXISTS idx_provider_usage_created_at ON provider_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_chats_provider_id ON chats(provider_id);
CREATE INDEX IF NOT EXISTS idx_chats_model_id ON chats(model_id);
CREATE INDEX IF NOT EXISTS idx_messages_provider_id ON messages(provider_id);
CREATE INDEX IF NOT EXISTS idx_messages_model_id ON messages(model_id);

-- Ensure only one default provider
CREATE UNIQUE INDEX idx_provider_configs_default ON provider_configs(is_default) WHERE is_default = TRUE;

-- Ensure only one default system prompt
CREATE UNIQUE INDEX idx_system_prompts_default ON system_prompts(is_default) WHERE is_default = TRUE;