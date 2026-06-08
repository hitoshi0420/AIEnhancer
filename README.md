# AIEnhancer - AI Video Quality Enhancer

AI-powered video upscaling tool based on Real-ESRGAN super-resolution.

## Features
- Batch video upscaling with AI super-resolution (Real-ESRGAN ncnn-vulkan)
- Dark-themed GUI built with CustomTkinter
- Real-time progress tracking with ETA
- Async processing for smooth UI experience

## Tech Stack
- Python 3.11+
- Real-ESRGAN (ncnn-vulkan engine)
- CustomTkinter (modern GUI)
- asyncio (async processing)

## Project Structure
`
AIEnhancer/
  main.py          # GUI application entry point
  upscaler.py       # Real-ESRGAN integration & video processing
  helpers.py        # Utility functions (time formatting, etc.)
  tools/            # Real-ESRGAN binaries & models (excluded from git)
`

## Setup
1. Download Real-ESRGAN from https://github.com/xinntao/Real-ESRGAN
2. Place 
ealesrgan-ncnn-vulkan.exe and models in 	ools/realesrgan/
3. Run the app:
`ash
pip install customtkinter
python main.py
`

## Usage
1. Launch the app
2. Select input video file
3. Choose upscale model (x2/x3/x4)
4. Click "Start" to begin processing
5. Output saved alongside the input file

## License
MIT
