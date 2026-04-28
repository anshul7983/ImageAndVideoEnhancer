import streamlit as st
import os
import subprocess
import shutil
import mimetypes
import sys
import torch

# --- Configuration ---
UPLOAD_FOLDER = 'upload'
RESULTS_FOLDER = 'results'

if os.path.exists(RESULTS_FOLDER):
    shutil.rmtree(RESULTS_FOLDER)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# --- AUTOMATIC FIXER ---
def create_fixed_scripts():
    scripts_to_fix = {
        "inference_realesrgan.py": "fixed_image.py",
        "inference_realesrgan_video.py": "fixed_video.py"
    }
    patch_code = """
import sys
import torchvision.transforms.functional as F
try:
    from torchvision.transforms import functional_tensor
except ImportError:
    sys.modules["torchvision.transforms.functional_tensor"] = F
"""
    for original, fixed in scripts_to_fix.items():
        if os.path.exists(original):
            with open(original, "r") as f:
                content = f.read()
            if "sys.modules" not in content:
                final_content = patch_code + "\n" + content
                with open(fixed, "w") as f:
                    f.write(final_content)

create_fixed_scripts()

# --- HELPER: Run Command with Live Logs ---
def run_command_with_logs(cmd):
    log_container = st.empty()
    logs = []
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            clean_line = line.strip()
            if clean_line:
                logs.append(clean_line)
                display_logs = "\n".join(logs[-20:]) 
                log_container.code(display_logs, language="bash")
    
    return process.poll()
    
# --- HELPER: GPU Info ---
def get_gpu_info():
    if torch.cuda.is_available():
        count = torch.cuda.device_count()
        name = torch.cuda.get_device_name(0)
        return True, f"{count}x {name}"
    return False, "CPU Only (Very Slow)"

# --- Model Options ---
MODELS = {
    'RealESRGAN_x4plus': 'General (Best for Real Life Photos)',
    'RealESRGAN_x4plus_anime_6B': 'Anime High-Quality (Best for Images)',
    'realesr-animevideov3': 'Anime Video V3 (Fast, Smooth, Best for Video)',
    'realesr-general-x4v3': 'General V3 (Tiny/Fast)'
}

st.title("Tx2 : Real-ESRGAN Automation")
st.markdown("Persistent Environment • Video Support • Live Logging")

# --- GPU Status ---
has_gpu, gpu_name = get_gpu_info()
if has_gpu:
    st.success(f"🚀 GPU Detected: **{gpu_name}**")
else:
    st.warning(f"⚠️ {gpu_name} - Processing will be slow.")

# --- Sidebar ---
st.sidebar.header("Settings")
selected_model = st.sidebar.selectbox("Choose Model", list(MODELS.keys()), format_func=lambda x: f"{x} - {MODELS[x]}")
out_scale = st.sidebar.slider("Upscale Factor", 1.0, 4.0, 4.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.header("Performance")

# Process Count Slider
# L4/T4 GPUs can usually handle 2-3 processes comfortably. 1 is safe default.
if has_gpu:
    process_count = st.sidebar.slider("GPU Processes (Video Only)", 1, 5, 2, help="Higher = Faster Video Processing. If it crashes, lower this value.")
else:
    process_count = 1

# Face enhance check
face_enhance = st.sidebar.checkbox("Face Enhancement (Images Only)", value=False)

# --- Main ---
uploaded_file = st.file_uploader("Upload File (Image or Video)", type=["png", "jpg", "jpeg", "webp", "mp4", "avi", "mov"])

if uploaded_file:
    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
    is_video = mime_type and mime_type.startswith('video')
    
    input_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Input")
        if is_video:
            st.video(input_path)
        else:
            st.image(input_path, use_column_width=True)

    if st.button("🚀 Run Upscaler"):
        st.info(f"Processing with {selected_model} on {gpu_name}")
        
        # Build Command
        if is_video:
            # Video Command with Parallel Processing
            cmd = [
                sys.executable, "fixed_video.py",
                "-i", input_path,
                "-o", RESULTS_FOLDER,
                "-n", selected_model,
                "-s", str(out_scale),
                "--suffix", "out",
                "--num_process_per_gpu", str(process_count) # <--- Added this flag
            ]
            name, ext = os.path.splitext(uploaded_file.name)
            output_filename = f"{name}_out.mp4" 
        else:
            # Image Command
            cmd = [
                sys.executable, "fixed_image.py",
                "-n", selected_model,
                "-i", input_path,
                "-o", RESULTS_FOLDER,
                "--outscale", str(out_scale),
                "--suffix", "out"
            ]
            if face_enhance:
                cmd.append("--face_enhance")
            name, ext = os.path.splitext(uploaded_file.name)
            output_filename = f"{name}_out{ext}"

        # RUN
        return_code = run_command_with_logs(cmd)

        if return_code == 0:
            output_path = os.path.join(RESULTS_FOLDER, output_filename)
            
            # Fallback check for video output names
            if not os.path.exists(output_path) and is_video:
                found_files = os.listdir(RESULTS_FOLDER)
                if found_files:
                    # Filter for video files only to avoid picking up frames folder
                    video_files = [f for f in found_files if f.endswith(('.mp4', '.avi', '.mov'))]
                    if video_files:
                        output_path = os.path.join(RESULTS_FOLDER, video_files[0])

            if os.path.exists(output_path):
                with col2:
                    st.subheader("Output")
                    if is_video:
                        st.video(output_path)
                    else:
                        st.image(output_path, use_column_width=True)
                
                st.success("Processing Complete!")
                with open(output_path, "rb") as f:
                    st.download_button(
                        "📥 Download Result",
                        data=f,
                        file_name=f"upscaled_{uploaded_file.name}",
                        mime=mime_type or "application/octet-stream"
                    )
            else:
                st.error("Output file missing. Check the logs above for errors.")
        else:
            st.error("Process failed. Check the logs above.")