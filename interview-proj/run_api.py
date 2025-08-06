#!/usr/bin/env python3
"""Run the API server"""
import uvicorn
import os
import sys

def main():
    """Main function to run the API"""
    print("🚀 Starting Jenosize Trend Articles Generator API...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("src/api/main.py"):
        print("❌ Error: src/api/main.py not found!")
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"📡 Starting server on http://{host}:{port}")
    print("📚 API Documentation will be available at:")
    print(f"   - Interactive docs: http://localhost:{port}/docs")
    print(f"   - ReDoc: http://localhost:{port}/redoc")
    print("📊 Health check: http://localhost:{port}/health")
    print()
    print("💡 Tip: Run 'streamlit run demo/app.py' in another terminal for the demo!")
    print("🔄 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "src.api.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()