import os
import urllib.request
import zipfile
import shutil

def download_ngrok():
    url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    zip_path = "ngrok.zip"
    
    print(f"Downloading ngrok from {url}...")
    try:
        # User agent sometimes required to avoid 403
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Download complete.")
        
        print("Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
            
        print("Extraction complete.")
        
        if os.path.exists("ngrok.exe"):
            print("SUCCESS: ngrok.exe is ready in the current directory.")
        else:
            print("ERROR: ngrok.exe was not found after extraction.")
            
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    download_ngrok()
