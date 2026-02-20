#!/bin/sh
set -e
python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port ${PORT:-8501}
