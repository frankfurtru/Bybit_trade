# File Structure Documentation

## Core Purpose: Each file has ONE clear responsibility

### 📁 **src/** - Main Application Code

#### 🔧 **Core System Files**
- **`main.py`** - MCP Server Implementation
  - Purpose: Main entry point, True MCP server with natural language understanding
  - Key: Single source of truth for MCP server functionality

- **`config.py`** - Configuration Management
  - Purpose: Environment variables, settings, configuration loading
  - Key: Centralized configuration management

#### 🌐 **Exchange Integration**
- **`bybit_client.py`** - Bybit Exchange Client
  - Purpose: Bybit-specific API calls and response formatting
  - Key: Dedicated Bybit integration

- **`exchange_client.py`** - Multi-Exchange Client
  - Purpose: Generic multi-exchange API wrapper
  - Key: Unified interface for multiple exchanges (Binance, KuCoin, etc.)

#### 🧠 **AI & Trading Intelligence**
- **`llm.py`** - LLM Client Interface
  - Purpose: LLM communication and response handling
  - Key: AI/LLM integration layer

- **`natural_trading_assistant.py`** - Trading Tools Registry
  - Purpose: Trading tools, functions, and execution registry
  - Key: Trading business logic and tool management

#### 🔐 **Security & Authentication**
- **`auth.py`** - Authentication System
  - Purpose: User authentication and session management
  - Key: Security layer for protected operations

#### 📊 **ML & Analytics** (Optional/Future)
- **`model.py`** - Base Model Classes
- **`xgb_model.py`** - XGBoost Implementation
- **`features.py`** - Feature Engineering
- **`strategy.py`** - Trading Strategies
  - Purpose: Machine learning and strategy components
  - Key: Analytics and prediction capabilities

#### 🔧 **Utilities**
- **`__init__.py`** - Package Initialization
  - Purpose: Python package setup

### 📁 **Root Level**

#### 🧪 **Testing**
- **`test_mcp_server.py`** - Comprehensive Test Suite
  - Purpose: Complete testing of MCP server, natural language, and API functionality
  - Key: Single test file covering all scenarios

## 🎯 **Clean Architecture Principles Applied:**

1. **Single Responsibility**: Each file has ONE clear purpose
2. **No Duplication**: Removed redundant files (`mcp_server.py`, `natural_language_processor.py`, `test_natural_language.py`)
3. **Clear Separation**: Exchange logic, AI logic, auth logic all separated
4. **Main Entry Point**: `main.py` is the single MCP server implementation
5. **Unified Testing**: One comprehensive test file

## 🚀 **Usage:**

```bash
# Run MCP Server
python src/main.py

# Run All Tests
python test_mcp_server.py
```

## ✅ **File Purposes Summary:**

| File | Purpose | Status |
|------|---------|--------|
| `main.py` | MCP Server | ✅ Single source |
| `config.py` | Configuration | ✅ Centralized |
| `llm.py` | AI Integration | ✅ Clean interface |
| `bybit_client.py` | Bybit API | ✅ Dedicated |
| `exchange_client.py` | Multi-exchange | ✅ Unified |
| `natural_trading_assistant.py` | Trading tools | ✅ Registry pattern |
| `auth.py` | Security | ✅ Separated |
| `test_mcp_server.py` | Testing | ✅ Comprehensive |

**Result: Clean, non-duplicated codebase with clear separation of concerns! 🎉**