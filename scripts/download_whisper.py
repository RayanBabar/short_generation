from faster_whisper import download_model
import shutil
import os

def download_whisper():
    output_dir = "models/whisper-medium-en"
    model_name = "medium.en"
    
    print(f"⬇️  Downloading '{model_name}' model to '{output_dir}'...")
    
    # Download to default cache
    model_path = download_model(model_name, output_dir=output_dir)
    
    print(f"✅ Model downloaded successfully to: {model_path}")
    print("\nNext steps:")
    print(f"1. Ensure .env has: WHISPER_MODEL_PATH={output_dir}")
    print("2. Restart the application")

if __name__ == "__main__":
    download_whisper()
