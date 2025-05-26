-- Seed data for multi-provider support
-- This adds initial provider configurations and models

-- Set schema to public
SET search_path TO public;

-- Insert provider configurations
INSERT INTO provider_configs (id, name, display_name, provider_type, base_url, api_key_env_var, is_active, is_default, config) VALUES
-- Ollama (default for backward compatibility)
(gen_random_uuid(), 'ollama', 'Ollama (Local)', 'ollama', 'http://localhost:11434', NULL, TRUE, TRUE, '{"timeout": 30}'),
-- Anthropic
(gen_random_uuid(), 'anthropic', 'Anthropic Claude', 'anthropic', 'https://api.anthropic.com', 'ANTHROPIC_API_KEY', TRUE, FALSE, '{"api_version": "2023-06-01", "timeout": 60}'),
-- OpenAI
(gen_random_uuid(), 'openai', 'OpenAI GPT', 'openai', 'https://api.openai.com/v1', 'OPENAI_API_KEY', TRUE, FALSE, '{"timeout": 60}'),
-- Google
(gen_random_uuid(), 'google', 'Google Gemini', 'google', 'https://generativelanguage.googleapis.com', 'GOOGLE_API_KEY', TRUE, FALSE, '{"timeout": 60}')
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    base_url = EXCLUDED.base_url,
    config = EXCLUDED.config,
    updated_at = CURRENT_TIMESTAMP;

-- Insert Ollama models (only the specific model requested)
INSERT INTO provider_models (provider_id, model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions) 
SELECT 
    pc.id,
    model.model_name,
    model.display_name,
    model.description,
    model.context_window,
    model.max_tokens,
    model.supports_streaming,
    model.supports_functions
FROM provider_configs pc
CROSS JOIN (VALUES 
    ('llama3.1:8b-instruct-q8_0', 'Llama 3.1 8B Instruct (Q8)', 'Meta Llama 3.1 8B Instruct quantized model', 128000, 128000, TRUE, FALSE)
) AS model(model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions)
WHERE pc.name = 'ollama'
ON CONFLICT (provider_id, model_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    context_window = EXCLUDED.context_window,
    max_tokens = EXCLUDED.max_tokens,
    updated_at = CURRENT_TIMESTAMP;

-- Insert Anthropic models (2025 models)
INSERT INTO provider_models (provider_id, model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions) 
SELECT 
    pc.id,
    model.model_name,
    model.display_name,
    model.description,
    model.context_window,
    model.max_tokens,
    model.supports_streaming,
    model.supports_functions
FROM provider_configs pc
CROSS JOIN (VALUES 
    ('claude-opus-4-20250514', 'Claude 4 Opus', 'Most powerful model for complex tasks', 200000, 32000, TRUE, TRUE),
    ('claude-sonnet-4-20250514', 'Claude 4 Sonnet', 'Balanced performance and efficiency', 200000, 32000, TRUE, TRUE),
    ('claude-3.7-sonnet-20250224', 'Claude 3.7 Sonnet', 'Hybrid reasoning with step-by-step thinking', 200000, 128000, TRUE, TRUE),
    ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 'Previous generation high capability', 200000, 8192, TRUE, TRUE),
    ('claude-3-5-haiku-20241022', 'Claude 3.5 Haiku', 'Fast and cost-effective', 200000, 8192, TRUE, TRUE)
) AS model(model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions)
WHERE pc.name = 'anthropic'
ON CONFLICT (provider_id, model_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    context_window = EXCLUDED.context_window,
    max_tokens = EXCLUDED.max_tokens,
    updated_at = CURRENT_TIMESTAMP;

-- Insert OpenAI models (2025 models)
INSERT INTO provider_models (provider_id, model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions) 
SELECT 
    pc.id,
    model.model_name,
    model.display_name,
    model.description,
    model.context_window,
    model.max_tokens,
    model.supports_streaming,
    model.supports_functions
FROM provider_configs pc
CROSS JOIN (VALUES 
    ('gpt-4.1', 'GPT-4.1', 'Latest GPT-4 with 1M context', 1000000, 32768, TRUE, TRUE),
    ('gpt-4.1-mini', 'GPT-4.1 Mini', 'Efficient model with 1M context', 1000000, 32768, TRUE, TRUE),
    ('gpt-4.1-nano', 'GPT-4.1 Nano', 'Most affordable with 1M context', 1000000, 32768, TRUE, TRUE),
    ('gpt-4o', 'GPT-4o', 'Multimodal model (text, image, audio)', 128000, 16384, TRUE, TRUE),
    ('gpt-4o-mini', 'GPT-4o Mini', 'Small, affordable, intelligent', 128000, 16384, TRUE, TRUE),
    ('gpt-4-turbo', 'GPT-4 Turbo', 'Previous generation with vision', 128000, 4096, TRUE, TRUE),
    ('gpt-3.5-turbo', 'GPT-3.5 Turbo', 'Fast and efficient legacy model', 16385, 4096, TRUE, TRUE)
) AS model(model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions)
WHERE pc.name = 'openai'
ON CONFLICT (provider_id, model_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    context_window = EXCLUDED.context_window,
    max_tokens = EXCLUDED.max_tokens,
    supports_streaming = EXCLUDED.supports_streaming,
    supports_functions = EXCLUDED.supports_functions,
    updated_at = CURRENT_TIMESTAMP;

-- Insert Google Gemini models (2025 models)
INSERT INTO provider_models (provider_id, model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions) 
SELECT 
    pc.id,
    model.model_name,
    model.display_name,
    model.description,
    model.context_window,
    model.max_tokens,
    model.supports_streaming,
    model.supports_functions
FROM provider_configs pc
CROSS JOIN (VALUES 
    ('gemini-2.5-pro', 'Gemini 2.5 Pro', 'Advanced model with built-in thinking', 1000000, 8192, TRUE, TRUE),
    ('gemini-2.5-flash', 'Gemini 2.5 Flash', 'Low latency, 20-30% more efficient', 1000000, 8192, TRUE, TRUE),
    ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash Experimental', 'Experimental features and capabilities', 1000000, 8192, TRUE, TRUE),
    ('gemini-1.5-pro', 'Gemini 1.5 Pro', 'Previous generation Pro model', 2097152, 8192, TRUE, TRUE),
    ('gemini-1.5-flash', 'Gemini 1.5 Flash', 'Previous generation Flash model', 1048576, 8192, TRUE, TRUE)
) AS model(model_name, display_name, description, context_window, max_tokens, supports_streaming, supports_functions)
WHERE pc.name = 'google'
ON CONFLICT (provider_id, model_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    context_window = EXCLUDED.context_window,
    max_tokens = EXCLUDED.max_tokens,
    supports_streaming = EXCLUDED.supports_streaming,
    supports_functions = EXCLUDED.supports_functions,
    updated_at = CURRENT_TIMESTAMP;

-- Add capabilities to models
UPDATE provider_models pm
SET capabilities = 
    CASE 
        -- Ollama models
        WHEN pm.model_name LIKE 'llama%' THEN 
            '{"code": true, "chat": true, "reasoning": true}'::jsonb
        -- Anthropic models
        WHEN pm.model_name LIKE 'claude-opus-4%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true, "advanced_reasoning": true}'::jsonb
        WHEN pm.model_name LIKE 'claude-sonnet-4%' OR pm.model_name LIKE 'claude-3.7%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true, "step_by_step_thinking": true}'::jsonb
        WHEN pm.model_name LIKE 'claude%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true}'::jsonb
        -- OpenAI models
        WHEN pm.model_name LIKE 'gpt-4.1%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true, "large_context": true}'::jsonb
        WHEN pm.model_name LIKE 'gpt-4o%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "audio": true, "multimodal": true}'::jsonb
        WHEN pm.model_name LIKE 'gpt-4%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true}'::jsonb
        WHEN pm.model_name LIKE 'gpt-3.5%' THEN 
            '{"code": true, "chat": true, "reasoning": true}'::jsonb
        -- Google models
        WHEN pm.model_name LIKE 'gemini-2.5%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true, "built_in_thinking": true, "live_api": true}'::jsonb
        WHEN pm.model_name LIKE 'gemini%' THEN 
            '{"code": true, "chat": true, "reasoning": true, "vision": true, "analysis": true, "large_context": true}'::jsonb
        ELSE 
            '{"code": true, "chat": true, "reasoning": true}'::jsonb
    END
WHERE capabilities IS NULL OR capabilities = '{}'::jsonb;