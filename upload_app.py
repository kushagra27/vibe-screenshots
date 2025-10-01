import os
import shutil
import subprocess
from pathlib import Path
from typing import List
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image
import pillow_heif

# Register HEIF opener for iOS photos
pillow_heif.register_heif_opener()

app = FastAPI(title="Screenshot Upload API", version="1.0.0")

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN", "your-secret-token-here")  # Change this!

# Paths
SOURCE_DIR = Path("source")
UPLOAD_DIR = SOURCE_DIR  # Images go directly to source directory

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != UPLOAD_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials

def is_valid_image(file_content: bytes) -> bool:
    """Check if uploaded file is a valid image"""
    try:
        Image.open(io.BytesIO(file_content))
        return True
    except Exception:
        return False

def regenerate_image_list():
    """Run lister.py to regenerate image_widths_heights.json"""
    try:
        result = subprocess.run(
            ["python3", "lister.py"], 
            cwd=SOURCE_DIR, 
            capture_output=True, 
            text=True,
            check=True
        )
        return {"success": True, "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}

@app.get("/", response_class=HTMLResponse)
async def upload_page():
    """Serve the upload interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Screenshot Upload</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                max-width: 800px; margin: 0 auto; padding: 20px;
                background: #f5f5f5;
            }
            .upload-area {
                border: 3px dashed #ccc; border-radius: 10px;
                padding: 40px; text-align: center; margin: 20px 0;
                background: white; cursor: pointer; transition: all 0.3s;
            }
            .upload-area:hover, .upload-area.drag-over {
                border-color: #007bff; background: #f8f9fa;
            }
            .file-input { display: none; }
            .upload-btn {
                background: #007bff; color: white; border: none;
                padding: 12px 24px; border-radius: 6px; cursor: pointer;
                font-size: 16px; margin: 10px;
            }
            .upload-btn:hover { background: #0056b3; }
            .status { 
                margin: 10px 0; padding: 10px; border-radius: 4px;
                display: none;
            }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .token-input {
                width: 100%; padding: 10px; margin: 10px 0;
                border: 1px solid #ddd; border-radius: 4px; font-size: 16px;
            }
            @media (max-width: 600px) {
                body { padding: 10px; }
                .upload-area { padding: 20px; }
            }
        </style>
    </head>
    <body>
        <h1>📸 Screenshot Upload</h1>
        
        <div>
            <input type="password" id="token" class="token-input" 
                   placeholder="Enter upload token" autocomplete="off">
        </div>
        
        <div class="upload-area" id="uploadArea">
            <h3>📤 Drop images here or click to select</h3>
            <p>Supports: JPG, PNG, HEIC, GIF, WebP</p>
            <input type="file" id="fileInput" class="file-input" 
                   multiple accept="image/*" capture="environment">
            <button class="upload-btn">Choose Files</button>
        </div>
        
        <div id="status" class="status"></div>
        
        <div id="previews"></div>

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const tokenInput = document.getElementById('token');
            const status = document.getElementById('status');
            const previews = document.getElementById('previews');

            // Load saved token
            tokenInput.value = localStorage.getItem('uploadToken') || '';

            // Save token when changed
            tokenInput.addEventListener('change', () => {
                localStorage.setItem('uploadToken', tokenInput.value);
            });

            uploadArea.addEventListener('click', () => fileInput.click());

            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('drag-over');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                handleFiles(e.dataTransfer.files);
            });

            fileInput.addEventListener('change', (e) => {
                handleFiles(e.target.files);
            });

            function showStatus(message, type) {
                status.textContent = message;
                status.className = `status ${type}`;
                status.style.display = 'block';
                setTimeout(() => status.style.display = 'none', 5000);
            }

            async function handleFiles(files) {
                if (!tokenInput.value.trim()) {
                    showStatus('Please enter your upload token', 'error');
                    return;
                }

                const formData = new FormData();
                for (let file of files) {
                    formData.append('files', file);
                }

                try {
                    showStatus('Uploading...', 'success');
                    const response = await fetch('/upload', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${tokenInput.value}`
                        },
                        body: formData
                    });

                    const result = await response.json();
                    
                    if (response.ok) {
                        showStatus(`✅ Uploaded ${result.uploaded_count} files successfully!`, 'success');
                        fileInput.value = '';
                    } else {
                        showStatus(`❌ Error: ${result.detail}`, 'error');
                    }
                } catch (error) {
                    showStatus(`❌ Upload failed: ${error.message}`, 'error');
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    _: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Upload multiple image files"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                errors.append(f"{file.filename}: Not an image file")
                continue
            
            # Read file content
            content = await file.read()
            
            # Validate it's actually an image
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()  # Verify it's not corrupted
            except Exception:
                errors.append(f"{file.filename}: Invalid or corrupted image")
                continue
            
            # Generate unique filename to avoid conflicts
            file_extension = Path(file.filename).suffix.lower()
            if not file_extension:
                file_extension = '.jpg'
            
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = UPLOAD_DIR / unique_filename
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(content)
            
            uploaded_files.append(unique_filename)
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    # Regenerate the image list
    regen_result = regenerate_image_list()
    
    response = {
        "uploaded_count": len(uploaded_files),
        "uploaded_files": uploaded_files,
        "errors": errors,
        "regeneration": regen_result
    }
    
    if errors and not uploaded_files:
        raise HTTPException(status_code=400, detail="All uploads failed", headers=response)
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "upload_dir": str(UPLOAD_DIR)}

if __name__ == "__main__":
    import uvicorn
    import io
    
    print("🚀 Starting upload server...")
    print(f"📁 Upload directory: {UPLOAD_DIR.absolute()}")
    print(f"🔑 Upload token: {UPLOAD_TOKEN}")
    print("🌐 Access upload interface at: http://localhost:8001")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)