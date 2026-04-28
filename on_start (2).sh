#!/bin/bash

# --- 1. SYSTEM CHECKS (FFmpeg) ---
# Installs system-level tools if they are missing (reset on restart)
if ! command -v ffmpeg &> /dev/null; then
    echo "🎥 FFmpeg not found. Installing System Tools..."
    sudo apt-get update -y
    sudo apt-get install -y ffmpeg
else
    echo "✅ FFmpeg system tool is ready."
fi

# --- 1.5. FETCH REAL-ESRGAN REPO FILES ---
# Clones the repo to a temp folder and moves it to the current directory
if [ ! -f "inference_realesrgan.py" ]; then
    echo "📥 Downloading missing Real-ESRGAN base files..."
    git clone https://github.com/xinntao/Real-ESRGAN.git temp_realesrgan
    cp -r temp_realesrgan/* .
    rm -rf temp_realesrgan
    echo "✅ Base files ready."
fi

# --- 1.6. DOWNLOAD PRE-TRAINED MODELS ---
# Downloads the required .pth files to the weights directory
mkdir -p weights
if [ ! -f "weights/RealESRGAN_x4plus.pth" ]; then
    - "📥 Downloading pre-trained model weights (this might take a minute)..."
    wget -q -O weights/RealESRGAN_x4plus.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
    wget -q -O weights/RealESRGAN_x4plus_anime_6B.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth
    wget -q -O weights/realesr-animevideov3.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth
    wget -q -O weights/realesr-general-x4v3.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth
    echo "✅ Models downloaded."
fi

# --- 2. PERSISTENT PYTHON ENVIRONMENT ---
ENV_DIR="persistent_env"

# Check if the persistent environment exists
if [ ! -d "$ENV_DIR" ]; then
    echo "🛠️  First run detected. Building persistent environment..."
    echo "This will take about 2-3 minutes. Please wait."
    
    # Create Virtual Env
    python3 -m venv $ENV_DIR
    source $ENV_DIR/bin/activate
    
    echo "📦 Installing PyTorch (CUDA)..."
    # L4 GPUs work well with CUDA 11.8 or 12.1. We stick to 11.8 for Real-ESRGAN compatibility.
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    
    echo "📦 Installing Real-ESRGAN dependencies..."
    # Install critical dependencies in specific order to avoid build errors
    pip install basicsr
    pip install facexlib
    pip install gfpgan
    pip install -r requirements.txt
    python setup.py develop
    
    echo "📦 Installing App dependencies..."
    # strict install of ffmpeg-python to avoid the wrapper conflict
    pip install streamlit ffmpeg-python opencv-python-headless
    
    echo "✅ Installation Complete!"
else
    echo "⚡ Persistent environment found. Skipping installation."
    source $ENV_DIR/bin/activate
fi

# --- 3. LAUNCH APP ---
echo "🚀 Starting Streamlit App..."
streamlit run app.py

# This script runs every time your Studio starts, from your home directory.

# Logs from previous runs can be found in ~/.lightning_studio/logs/

# List files under fast_load that need to load quickly on start (e.g. model checkpoints).
#
# ! fast_load
# <your file here>

# Add your startup commands below.
#
# Example: streamlit run my_app.py
# Example: gradio my_app.py