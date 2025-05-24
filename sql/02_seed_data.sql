-- Seed data for initial application setup

-- Insert default admin user (password: admin)
-- In production, use proper password hashing
INSERT INTO users (username, email, hashed_password, api_key, is_admin)
VALUES (
    'admin',
    'admin@example.com',
    -- This is a placeholder. In production, use proper password hashing
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 
    '5ffca2729f69d50cad703e95a313255d',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Insert default system prompt
INSERT INTO system_prompts (name, content, description)
VALUES (
    'Default', 
    'You are a helpful AI assistant. Answer the user''s questions concisely and accurately.', 
    'Default system prompt for general-purpose conversation'
) ON CONFLICT (name) DO NOTHING;

-- Insert example system prompt for coding assistance
INSERT INTO system_prompts (name, content, description)
VALUES (
    'Code Assistant', 
    'You are a programming assistant. Help users with coding problems, explain concepts, and provide code examples when requested. Focus on providing correct, efficient, and easy-to-understand code.', 
    'System prompt optimized for programming help'
) ON CONFLICT (name) DO NOTHING;