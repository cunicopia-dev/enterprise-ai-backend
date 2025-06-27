# Streamlit App Wireframes

## Overview Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Top Navigation Bar                               │
│ [🤖 FastAPI LLM] [Mode: Chat ▼] [Status: 🟢 Connected] [⚙️] [👤 User ▼]   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Sidebar │                         Main Content Area                         │
│ (250px) │                           (Flexible)                              │
│         │                                                                   │
│  [📝]   │   Dynamic content based on selected mode:                        │
│  Chat   │   • Chat Interface (default)                                     │
│         │   • Prompt Studio                                                 │
│  [🎯]   │   • MCP Control Center                                           │
│  Prompts│   • Settings                                                      │
│         │                                                                   │
│  [🔧]   │                                                                   │
│  MCP    │                                                                   │
│         │                                                                   │
│  [⚙️]   │                                                                   │
│  Settings                                                                   │
│         │                                                                   │
│ ┌─────┐ │                                                                   │
│ │Chat │ │                                                                   │
│ │List │ │                                                                   │
│ └─────┘ │                                                                   │
└─────────┴───────────────────────────────────────────────────────────────────┘
```

## Mode 1: Chat Interface

```
┌─── Chat Mode ───────────────────────────────────────────────────────────────┐
│ Model: [Anthropic Claude 3.5 Haiku ▼] Tokens: 1,234 Cost: $0.03 MCP: 🟢  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─ Messages ──────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │ 👤 User • 2:34 PM                                          [📋][✏️][🔄] │ │
│ │ Create a test file with the content "Hello MCP"                         │ │
│ │                                                                         │ │
│ │ 🤖 Claude 3.5 Haiku • 2:34 PM                              [📋][✏️][🔄] │ │
│ │ I'll create a test file for you with the content "Hello MCP".          │ │
│ │                                                                         │ │
│ │ ┌─ 🔧 Tool Executions ─────────────────────────────────────────────────┐ │ │
│ │ │ **Round 1:**                                                        │ │ │
│ │ │ • `filesystem__write_file(path="test.txt", content="Hello MCP")`   │ │ │
│ │ │   → ✅ Successfully wrote to test.txt                               │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │ The file has been created successfully at test.txt                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─ Message Input ────────────────────────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────┐ [Send] [🎤] [📎] │ │
│ │ │ Type your message...                            │               │ │
│ │ │ (Ctrl+Enter to send)                           │               │ │
│ │ │                                                 │               │ │
│ │ └─────────────────────────────────────────────────┘               │ │
│ │ [Clear] [New Chat] [Export]                         [Token: 45]    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Mode 2: Prompt Studio

```
┌─── Prompt Studio ───────────────────────────────────────────────────────────┐
│ Active Prompt: [Helpful Assistant ▼] [Edit] [Duplicate] [New] [Import]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Prompt Library ────────────────┐ ┌─ Editor ─────────────────────────────┐ │
│ │ 📁 System Prompts               │ │ Name: Helpful Assistant              │ │
│ │ ├── 📁 General                  │ │ ┌─────────────────────────────────────┐ │ │
│ │ │   ├── ⭐ Helpful Assistant    │ │ │ You are a helpful AI assistant     │ │ │
│ │ │   ├── 💻 Code Expert          │ │ │ focused on providing accurate,      │ │ │
│ │ │   ├── ✍️ Creative Writer     │ │ │ clear, and useful information.      │ │ │
│ │ │   └── 🔬 Research Assistant  │ │ │                                     │ │ │
│ │ ├── 📁 Custom                   │ │ │ You have access to various tools    │ │ │
│ │ │   ├── Customer Support        │ │ │ through MCP that you can use to     │ │ │
│ │ │   └── Data Analyst            │ │ │ help users accomplish tasks.        │ │ │
│ │ └── [+ New Category]            │ │ │                                     │ │ │
│ │                                 │ │ │ Always be polite, professional,    │ │ │
│ │ ┌─ Actions ──────────────────────┤ │ │ and thorough in your responses.     │ │ │
│ │ │ [Activate] [Edit] [Delete]    │ │ └─────────────────────────────────────┘ │ │
│ │ │ [Export] [Share]              │ │                                       │ │
│ │ └───────────────────────────────┤ │ ┌─ Preview ───────────────────────────┐ │ │
│ │                                 │ │ │ Test with: "Help me write a poem"  │ │ │
│ │ ┌─ Import/Export ───────────────┤ │ │ ┌─────────────────────────────────────┐ │ │
│ │ │ [📥 Import JSON]              │ │ │ │ I'd be happy to help you write a   │ │ │
│ │ │ [📤 Export Selected]          │ │ │ │ poem! What kind of poem would you   │ │ │
│ │ │ [🔗 Share URL]               │ │ │ │ like to create? Please let me know  │ │ │
│ │ └───────────────────────────────┘ │ │ │ the theme, style, or any specific   │ │ │
│ └─────────────────────────────────┘ │ │ │ requirements you have in mind.      │ │ │
│                                     │ │ └─────────────────────────────────────┘ │ │
│                                     │ │ [Save] [Discard] [Test Live]         │ │
│                                     │ └───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Mode 3: MCP Control Center

```
┌─── MCP Control Center ──────────────────────────────────────────────────────┐
│ Status: Connected 3/4 • Tools: 28 Available • [Refresh All] [View Logs]    │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Server Status ────────────────────────────────────────────────────────┐ │
│ │                                                                        │ │
│ │ ✅ filesystem • 12 tools • Connected                       [Disable]  │ │
│ │    📁 Allowed: /Users/user/projects/                                  │ │
│ │    🔧 write_file, read_file, create_directory, list_files...          │ │
│ │    ──────────────────────────────────────────────────────────────────  │ │
│ │                                                                        │ │
│ │ ✅ github • 8 tools • Connected                            [Disable]  │ │
│ │    🐙 Repository: anthropics/mcp                                      │ │
│ │    🔧 create_issue, search_code, get_pull_request...                  │ │
│ │    ──────────────────────────────────────────────────────────────────  │ │
│ │                                                                        │ │
│ │ ✅ memory • 8 tools • Connected                            [Disable]  │ │
│ │    🧠 Storage: In-memory (session)                                    │ │
│ │    🔧 store_memory, recall_memory, list_memories...                   │ │
│ │    ──────────────────────────────────────────────────────────────────  │ │
│ │                                                                        │ │
│ │ ❌ notion • Connection Failed                               [Retry]   │ │
│ │    ⚠️ Error: Invalid NOTION_TOKEN in environment                      │ │
│ │    💡 Fix: Set NOTION_TOKEN environment variable                      │ │
│ │                                                                        │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─ Quick Actions ────────────────────────────────────────────────────────┐ │
│ │ [+ Add Server] [📝 Edit Config] [🔄 Restart All] [🗑️ Remove Failed]  │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─ Tool Browser ─────────────────────────────────────────────────────────┐ │
│ │ Filter: [All Tools ▼] [🔍 Search...]                                  │ │
│ │                                                                        │ │
│ │ 📁 filesystem (12 tools)                                              │ │
│ │ ├── 📄 write_file(path, content) - Write content to a file            │ │
│ │ ├── 📖 read_file(path) - Read content from a file                     │ │
│ │ ├── 📁 create_directory(path) - Create a new directory                │ │
│ │ └── 📋 list_files(path) - List files in directory                     │ │
│ │                                                                        │ │
│ │ 🐙 github (8 tools)                                                   │ │
│ │ ├── 🎫 create_issue(title, body) - Create a new issue                 │ │
│ │ ├── 🔍 search_code(query) - Search code in repository                 │ │
│ │ └── 📊 get_pull_request(number) - Get PR details                      │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Sidebar: Chat Sessions

```
┌─ Chat Sessions ────────────┐
│ 🔍 Search chats...         │
├────────────────────────────┤
│ [+ New Chat]               │
├────────────────────────────┤
│ Today                      │
│ • 🟢 MCP Testing (2:34 PM) │
│ • Code Review (11:20 AM)   │
│ • API Questions (9:15 AM)  │
│                            │
│ Yesterday                  │
│ • Project Planning         │
│ • Bug Investigation        │
│ • Feature Discussion       │
│                            │
│ This Week                  │
│ • Database Design          │
│ • Performance Testing      │
│ • User Interface Ideas     │
│                            │
│ ┌─ Quick Stats ──────────┐ │
│ │ Total: 47 chats        │ │
│ │ Today: 3 chats         │ │
│ │ Tokens: 45.2K          │ │
│ │ Cost: $12.50           │ │
│ └────────────────────────┘ │
│                            │
│ [📤 Export All]            │
│ [🗑️ Cleanup Old]           │
└────────────────────────────┘
```

## Command Palette (Overlay)

```
                    ┌─ Command Palette ──────────────────┐
                    │ > switch model claude              │
                    ├────────────────────────────────────┤
                    │ 📋 Recent Commands                 │
                    │ • Switch to Claude 3.5 Haiku     │
                    │ • New Chat                        │
                    │ • Toggle MCP: filesystem          │
                    │                                   │
                    │ 🎯 Available Commands             │
                    │ • chat: New conversation          │
                    │ • model: Switch model             │
                    │ • prompt: Change system prompt    │
                    │ • mcp: Toggle server             │
                    │ • settings: Open preferences     │
                    │ • export: Download chat history   │
                    │                                   │
                    │ 🔧 MCP Commands                   │
                    │ • mcp status: View server status  │
                    │ • mcp enable: Enable server       │
                    │ • mcp disable: Disable server     │
                    │ • mcp tools: Browse available     │
                    └────────────────────────────────────┘
```

## Mobile/Responsive View

```
┌─────────────────────────────────┐ ← Collapsed sidebar on mobile
│ ☰ FastAPI LLM    🟢 Connected  │
├─────────────────────────────────┤
│                                 │
│ Model: Claude 3.5 Haiku ▼      │
│ Tokens: 1,234  MCP: 🟢         │
│                                 │
│ ┌─ Messages ──────────────────┐ │
│ │                             │ │
│ │ 👤 Create a test file       │ │
│ │                             │ │
│ │ 🤖 I'll help you...         │ │
│ │ 🔧 filesystem__write_file() │ │
│ │ ✅ Success                  │ │
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Your message...             │ │
│ │                             │ │
│ └─────────────────────────────┘ │
│ [Send]  [🎤]  [📎]  [⚙️]       │
└─────────────────────────────────┘
```

## Settings/Preferences

```
┌─── Settings ────────────────────────────────────────────────────────────────┐
│ ┌─ Appearance ────────────────┐ ┌─ API Configuration ──────────────────────┐ │
│ │ Theme: [Dark ▼]             │ │ Base URL: http://localhost:8000          │ │
│ │ ✅ Smooth animations        │ │ API Key: ••••••••••••••••••••••••••••••  │ │
│ │ ✅ Auto-scroll messages     │ │ Timeout: 30 seconds                      │ │
│ │ ✅ Syntax highlighting      │ │ [Test Connection]                        │ │
│ │ Message font: [Monospace ▼] │ │                                          │ │
│ └─────────────────────────────┘ └──────────────────────────────────────────┘ │
│                                                                             │
│ ┌─ Chat Behavior ─────────────┐ ┌─ MCP Settings ───────────────────────────┐ │
│ │ Auto-save: ✅ Enabled       │ │ Config File: mcp_servers_config.json     │ │
│ │ History: Keep 30 days       │ │ Auto-reconnect: ✅ Enabled               │ │
│ │ ✅ Stream responses         │ │ Timeout: 10 seconds                      │ │
│ │ ✅ Show tool executions     │ │ Max retries: 3                          │ │
│ │ ✅ Enable shortcuts         │ │ [Edit Config] [View Logs]                │ │
│ └─────────────────────────────┘ └──────────────────────────────────────────┘ │
│                                                                             │
│ ┌─ Performance ───────────────┐ ┌─ Data & Privacy ─────────────────────────┐ │
│ │ Max messages: 100           │ │ ✅ Store chat history locally            │ │
│ │ Cache duration: 5 minutes   │ │ ❌ Share usage analytics                 │ │
│ │ ✅ Lazy load old messages   │ │ ❌ Auto-backup to cloud                  │ │
│ │ Memory limit: 500MB         │ │ [Export Data] [Delete All]               │ │
│ └─────────────────────────────┘ └──────────────────────────────────────────┘ │
│                                                                             │
│ [Save Changes] [Reset to Defaults] [Import Settings] [Export Settings]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Loading States

```
┌─ Loading Examples ──────────────────────────────────────────────────────────┐
│                                                                             │
│ Connecting to API...                                                        │
│ ███████████████████████████████████████████████░░░░░░░░░░ 85%              │
│                                                                             │
│ 🤖 Generating response...                                                   │
│ ▓▓▓░░░▓▓▓░░░▓▓▓░░░  Thinking...                                            │
│                                                                             │
│ 🔧 Executing tools...                                                       │
│ • filesystem__write_file() ✅                                              │
│ • filesystem__read_file() ⏳                                               │
│ • github__search_code() ⏸️                                                 │
│                                                                             │
│ 📡 Connecting to MCP servers...                                             │
│ • filesystem: ✅ Connected                                                 │
│ • github: 🔄 Connecting...                                                │
│ • notion: ❌ Failed (retrying...)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Error States

```
┌─ Error Examples ────────────────────────────────────────────────────────────┐
│                                                                             │
│ ❌ API Connection Failed                                                    │
│ Unable to connect to FastAPI backend at http://localhost:8000              │
│ [Retry] [Check Settings] [Use Offline Mode]                                │
│                                                                             │
│ ⚠️ Rate Limit Exceeded                                                      │
│ You've reached your hourly limit of 1000 requests.                         │
│ Resets in: 23 minutes                                                       │
│ [Upgrade Plan] [View Usage]                                                │
│                                                                             │
│ 🔧 MCP Server Error                                                         │
│ filesystem server disconnected unexpectedly                                │
│ Error: Permission denied accessing /restricted/path                         │
│ [Reconnect] [View Logs] [Edit Config]                                      │
│                                                                             │
│ 💰 Cost Alert                                                               │
│ Daily spending has reached $10.00 (80% of limit)                           │
│ Current session: $2.50                                                      │
│ [Continue] [Set New Limit] [View Details]                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```