# Modular Streamlit App Design

## Design Philosophy

### Core Principles
1. **Minimalist**: Show only what's needed, when it's needed
2. **Modular**: Each feature is a self-contained module
3. **Intuitive**: Zero learning curve for basic usage
4. **Powerful**: Advanced features accessible but not intrusive
5. **Responsive**: Real-time feedback and status updates
6. **Keyboard-First**: Full keyboard navigation support

## Application Architecture

```
StreamlitApp/
├── app.py                  # Main entry point
├── config/
│   └── theme.py           # UI theme configuration
├── modules/
│   ├── __init__.py
│   ├── chat.py            # Chat interface module
│   ├── models.py          # Model selection module
│   ├── prompts.py         # System prompt manager
│   ├── mcp.py             # MCP server control
│   ├── sessions.py        # Chat session manager
│   └── settings.py        # Global settings
├── components/
│   ├── __init__.py
│   ├── message.py         # Message display component
│   ├── status.py          # Status indicators
│   ├── modal.py           # Modal dialogs
│   └── command_palette.py # Command palette (Cmd+K)
├── state/
│   ├── __init__.py
│   ├── manager.py         # Centralized state management
│   └── persistence.py     # State persistence
└── utils/
    ├── __init__.py
    ├── api_client.py      # FastAPI client
    ├── shortcuts.py       # Keyboard shortcuts
    └── animations.py      # Smooth transitions
```

## UI Layout Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                          Top Bar                                 │
│  [Logo] FastAPI LLM Platform    [Status: Connected] [User Menu] │
├─────────────────────────────────────────────────────────────────┤
│         │                                                        │
│         │                    Main Area                           │
│ Sidebar │                                                        │
│         │   Dynamic content based on selected mode               │
│ [Mode]  │                                                        │
│ [Tools] │                                                        │
│ [Chats] │                                                        │
│         │                                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Navigation Modes

1. **Chat Mode** (Default)
2. **Prompt Studio** 
3. **MCP Control Center**
4. **Settings**

## Module Specifications

### 1. Chat Module (`modules/chat.py`)

**Features:**
- Message input with multi-line support
- Real-time streaming responses
- Tool execution visualization
- Message history with search
- Copy/Edit/Regenerate message actions
- File upload support (future)

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Model: [Anthropic Claude 3.5] ▼  Token Count: 1,234 │
├─────────────────────────────────────────────────────┤
│                                                     │
│                 Message History                     │
│                                                     │
│  [User]   Create a test file                       │
│  [AI]     I'll create a test file for you...      │
│           🔧 Tool: filesystem__write_file()         │
│           ✓ Successfully created test.txt           │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Type your message... (Ctrl+Enter to send)         │
│  [Send] [Clear] [New Chat]          [Mic] [Upload] │
└─────────────────────────────────────────────────────┘
```

**State Management:**
```python
chat_state = {
    "current_chat_id": str,
    "messages": List[Message],
    "is_streaming": bool,
    "selected_model": str,
    "selected_provider": str,
    "tool_executions": List[ToolExecution]
}
```

### 2. Model Selector Module (`modules/models.py`)

**Features:**
- Provider selection with health status
- Model selection with capabilities
- Quick switch via keyboard (Ctrl+M)
- Favorites/Recent models
- Cost estimation display

**Component Design:**
```
Provider: [Anthropic ✓] ▼
├── Claude 3.5 Haiku (Fast, $0.25/1M)
├── Claude 3.5 Sonnet (Balanced, $3/1M) ⭐
└── Claude Opus 4 (Powerful, $15/1M)

[OpenAI ✓] [Google ✓] [Ollama ✓]
```

### 3. System Prompt Manager (`modules/prompts.py`)

**Features:**
- Prompt library with categories
- Live preview while editing
- Version history
- Import/Export prompts
- Quick switch (Ctrl+P)

**Interface:**
```
┌─ System Prompts ────────────────────────────────────┐
│ Active: "Helpful Assistant" (Default)               │
├─────────────────────────────────────────────────────┤
│ Library:                                            │
│ ├── 📁 General                                      │
│ │   ├── Helpful Assistant ⭐                        │
│ │   ├── Code Expert                                 │
│ │   └── Creative Writer                             │
│ ├── 📁 Custom                                       │
│ │   └── [+ New Prompt]                             │
│                                                     │
│ [Edit] [Duplicate] [Delete] [Export]               │
└─────────────────────────────────────────────────────┘
```

### 4. MCP Control Center (`modules/mcp.py`)

**Features:**
- Server status dashboard
- One-click enable/disable
- Tool discovery browser
- Connection logs
- Configuration editor

**Dashboard View:**
```
┌─ MCP Servers ───────────────────────────────────────┐
│ Connected: 2/4                                      │
├─────────────────────────────────────────────────────┤
│ ✅ filesystem (12 tools)                   [Disable]│
│    📁 write_file, read_file, create_dir...         │
│                                                     │
│ ✅ github (8 tools)                       [Disable]│
│    🐙 create_issue, search_code, get_pr...         │
│                                                     │
│ ❌ notion (Connection failed)            [Retry]   │
│    ⚠️ Check NOTION_TOKEN in environment            │
│                                                     │
│ ⭕ memory (Disabled)                     [Enable]  │
│                                                     │
│ [+ Add Server] [Refresh All] [View Logs]           │
└─────────────────────────────────────────────────────┘
```

### 5. Session Manager (`modules/sessions.py`)

**Features:**
- Chat history browser
- Search across all chats
- Bulk operations
- Export conversations
- Quick switch (Ctrl+H)

**Sidebar Component:**
```
┌─ Chat Sessions ─────────────┐
│ 🔍 Search...               │
├─────────────────────────────┤
│ Today                      │
│ • MCP Testing (2:34 PM) 🟢 │
│ • Code Review (11:20 AM)   │
│                            │
│ Yesterday                  │
│ • Project Planning         │
│ • Bug Investigation        │
│                            │
│ [+ New Chat] [Import]      │
└─────────────────────────────┘
```

## Component Library

### 1. Message Component (`components/message.py`)

```python
@dataclass
class MessageComponent:
    role: str  # user, assistant, tool
    content: str
    timestamp: datetime
    model: Optional[str]
    tool_calls: Optional[List[ToolCall]]
    
    def render(self):
        # Markdown rendering with syntax highlighting
        # Tool execution visualization
        # Copy/Edit actions on hover
```

### 2. Status Indicators (`components/status.py`)

- Connection status (API, MCP servers)
- Model health
- Rate limit warnings
- Token usage
- Cost tracking

### 3. Command Palette (`components/command_palette.py`)

**Activation: Cmd/Ctrl + K**

```
┌─ Command Palette ───────────────────────────────────┐
│ > _                                                 │
├─────────────────────────────────────────────────────┤
│ Recent:                                             │
│   Switch to Claude 3.5 Haiku                       │
│   New Chat                                         │
│   Toggle MCP: filesystem                           │
│                                                     │
│ Commands:                                          │
│   chat: New conversation                           │
│   model: Switch model                              │
│   prompt: Change system prompt                     │
│   mcp: Toggle server                               │
│   settings: Open preferences                       │
└─────────────────────────────────────────────────────┘
```

## State Management Strategy

### Centralized State Manager

```python
class AppState:
    def __init__(self):
        self.chat = ChatState()
        self.models = ModelState()
        self.prompts = PromptState()
        self.mcp = MCPState()
        self.ui = UIState()
        
    def persist(self):
        # Save to session state
        
    def restore(self):
        # Load from session state
        
    @property
    def context(self):
        # Get current context for API calls
        return {
            "chat_id": self.chat.current_id,
            "model": self.models.selected,
            "prompt": self.prompts.active,
            "mcp_tools": self.mcp.enabled_tools
        }
```

### Session State Keys

```python
# Persistent across reruns
st.session_state.app_state = AppState()
st.session_state.api_client = APIClient()

# UI state
st.session_state.ui = {
    "mode": "chat",  # chat, prompts, mcp, settings
    "theme": "dark",
    "sidebar_collapsed": False,
    "command_palette_open": False
}
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Open command palette |
| `Cmd/Ctrl + N` | New chat |
| `Cmd/Ctrl + M` | Quick model switch |
| `Cmd/Ctrl + P` | Quick prompt switch |
| `Cmd/Ctrl + /` | Toggle sidebar |
| `Cmd/Ctrl + Enter` | Send message |
| `Cmd/Ctrl + L` | Clear chat |
| `Cmd/Ctrl + S` | Save/Export chat |
| `Esc` | Close modal/palette |

## Theme System

### Dark Theme (Default)

```python
DARK_THEME = {
    "bg_primary": "#0E1117",
    "bg_secondary": "#262730", 
    "bg_tertiary": "#1C1C1C",
    "text_primary": "#FAFAFA",
    "text_secondary": "#B3B3B3",
    "accent": "#FF4B4B",  # Streamlit red
    "success": "#00CC88",
    "warning": "#FFA500",
    "error": "#FF4444",
    "border": "#363636"
}
```

### CSS Architecture

```css
/* Modular CSS with CSS variables */
:root {
    --bg-primary: #0E1117;
    --radius: 8px;
    --transition: all 0.2s ease;
}

/* Component-scoped styles */
.chat-message {
    background: var(--bg-secondary);
    border-radius: var(--radius);
    transition: var(--transition);
}

.chat-message:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. Set up modular architecture
2. Implement state management
3. Create base components
4. API client integration

### Phase 2: Essential Modules
1. Chat module with streaming
2. Model selector
3. Basic session management
4. Status indicators

### Phase 3: Advanced Features
1. System prompt manager
2. MCP control center
3. Command palette
4. Keyboard shortcuts

### Phase 4: Polish
1. Animations and transitions
2. Theme customization
3. Export/Import features
4. Performance optimization

## Performance Considerations

1. **Lazy Loading**: Load modules only when needed
2. **Debouncing**: Debounce API calls during typing
3. **Caching**: Cache model lists, prompts, etc.
4. **Virtual Scrolling**: For long chat histories
5. **Progressive Enhancement**: Basic features work instantly

## Mobile Responsiveness

- Collapsible sidebar on mobile
- Touch-friendly controls
- Swipe gestures for navigation
- Optimized layouts for small screens

## Future Enhancements

1. **Voice Input/Output**: Speech-to-text and TTS
2. **Collaborative Chats**: Share sessions with team
3. **Plugin System**: Custom modules and tools
4. **Themes Marketplace**: Community themes
5. **Analytics Dashboard**: Usage statistics
6. **Multimodal Support**: Image/File uploads