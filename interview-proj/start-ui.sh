#!/bin/bash

# Production startup script for Streamlit on Render
export PYTHONPATH="/opt/render/project/src:$PYTHONPATH"

# Start the Streamlit application
exec streamlit run demo/app.py \
    --server.port ${PORT:-8501} \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false