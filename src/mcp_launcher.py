#!/usr/bin/env python3
"""
MCP Server Launcher using FastAPI MCP Framework
Launches the enhanced MCP server with comprehensive API documentation context
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_mcp_server import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main launcher for the enhanced MCP server"""
    
    logger.info("🚀 Starting Enhanced MCP Server with FastAPI MCP Framework")
    logger.info("📚 Using comprehensive API documentation as context")
    logger.info("🔧 Server: FastAPI MCP with complete exchange API support")
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "http":
            # HTTP mode for testing
            import uvicorn
            logger.info("🌐 Running in HTTP mode for testing")
            uvicorn.run(app.app, host="0.0.0.0", port=8000)
        else:
            # Standard MCP mode
            logger.info("📡 Running in MCP mode")
            await app.run()
            
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())