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
            ["/var/www/vibe-screenshots/venv/bin/python3", "lister.py"],
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
                -webkit-text-size-adjust: 100%;
            }
            h1 {
                text-align: center; margin-bottom: 10px;
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
            .paste-btn { background: #6c757d; }
            .paste-btn:hover { background: #5a6268; }
            .status {
                margin: 10px 0; padding: 10px; border-radius: 4px;
                display: none;
            }
            .preview-container {
                display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0;
            }
            .preview-item {
                position: relative; border: 2px solid #ddd; border-radius: 8px;
                padding: 5px; background: white; max-width: 200px;
            }
            .preview-item img {
                width: 100%; height: auto; border-radius: 4px;
            }
            .preview-remove {
                position: absolute; top: -8px; right: -8px;
                background: #dc3545; color: white; border: none;
                border-radius: 50%; width: 24px; height: 24px;
                cursor: pointer; font-size: 14px; line-height: 1;
            }
            .preview-remove:hover { background: #c82333; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .token-input {
                width: 100%; padding: 12px; margin: 10px 0;
                border: 1px solid #ddd; border-radius: 4px; font-size: 16px;
            }
            .paste-area {
                width: 100%; min-height: 120px; padding: 15px;
                border: 2px dashed #007bff; border-radius: 8px;
                background: #f8f9fa; margin: 15px 0;
                font-size: 16px; resize: vertical;
                font-family: inherit;
            }
            .paste-area:focus {
                outline: none; border-color: #0056b3;
                background: white;
            }
            .paste-instruction {
                text-align: center; color: #6c757d;
                margin: 10px 0; font-size: 14px;
            }
            @media (max-width: 600px) {
                body { padding: 10px; }
                .upload-area { padding: 20px; }
                .upload-btn {
                    padding: 14px 20px; font-size: 16px;
                    width: 100%; margin: 5px 0;
                }
                h1 { font-size: 24px; }
                .preview-item { max-width: 150px; }
            }
        </style>
    </head>
    <body>
        <h1>📸 Screenshot Upload</h1>

        <div>
            <input type="password" id="token" class="token-input"
                   placeholder="Enter upload token" autocomplete="off">
        </div>

        <!-- Mobile-friendly paste area -->
        <div class="paste-instruction">
            📋 <strong>Paste images here</strong> (tap and hold to paste on mobile)
        </div>
        <textarea id="pasteArea" class="paste-area"
                  placeholder="Tap here and paste your screenshot... (long press and select Paste on mobile)"></textarea>

        <div style="text-align: center; margin: 15px 0; color: #6c757d;">
            — OR —
        </div>

        <div class="upload-area" id="uploadArea">
            <h3>📤 Drop or select files</h3>
            <p>Supports: JPG, PNG, HEIC, GIF, WebP</p>
            <input type="file" id="fileInput" class="file-input"
                   multiple accept="image/*">
            <button class="upload-btn">Choose Files</button>
        </div>

        <div id="status" class="status"></div>

        <div id="previews" style="margin: 20px 0;"></div>

        <button id="submitBtn" class="upload-btn" style="display: none; width: 100%; background: #28a745;">
            Upload Selected Images
        </button>

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const tokenInput = document.getElementById('token');
            const status = document.getElementById('status');
            const previews = document.getElementById('previews');
            const submitBtn = document.getElementById('submitBtn');
            const pasteArea = document.getElementById('pasteArea');

            let selectedFiles = [];

            // Load saved token
            tokenInput.value = localStorage.getItem('uploadToken') || '';

            // Save token when changed
            tokenInput.addEventListener('change', () => {
                localStorage.setItem('uploadToken', tokenInput.value);
            });

            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });

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
                addFiles(e.dataTransfer.files);
            });

            fileInput.addEventListener('change', (e) => {
                addFiles(e.target.files);
            });

            // Paste area handler
            pasteArea.addEventListener('paste', (e) => {
                e.preventDefault();
                const items = e.clipboardData.items;
                let foundImage = false;
                for (let item of items) {
                    if (item.type.startsWith('image/')) {
                        const file = item.getAsFile();
                        if (file) {
                            addFiles([file]);
                            foundImage = true;
                        }
                    }
                }
                if (foundImage) {
                    showStatus('✅ Image pasted! Review and click Upload.', 'success');
                    pasteArea.value = '';
                } else {
                    showStatus('No image found in clipboard', 'error');
                }
            });

            // Clear placeholder text on focus
            pasteArea.addEventListener('focus', () => {
                pasteArea.placeholder = 'Paste now...';
            });

            pasteArea.addEventListener('blur', () => {
                pasteArea.placeholder = 'Tap here and paste your screenshot... (long press and select Paste on mobile)';
            });

            // Global paste handler for convenience
            document.addEventListener('paste', (e) => {
                // Skip if pasting in the textarea (it has its own handler)
                if (e.target === pasteArea) return;

                const items = e.clipboardData.items;
                let foundImage = false;
                for (let item of items) {
                    if (item.type.startsWith('image/')) {
                        const file = item.getAsFile();
                        if (file) {
                            addFiles([file]);
                            foundImage = true;
                        }
                    }
                }
                if (foundImage) {
                    showStatus('✅ Image pasted! Review and click Upload.', 'success');
                }
            });

            function addFiles(files) {
                for (let file of files) {
                    if (file.type.startsWith('image/')) {
                        selectedFiles.push(file);
                    }
                }
                updatePreviews();
            }

            function updatePreviews() {
                previews.innerHTML = '';
                if (selectedFiles.length === 0) {
                    submitBtn.style.display = 'none';
                    return;
                }

                previews.className = 'preview-container';
                selectedFiles.forEach((file, index) => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const div = document.createElement('div');
                        div.className = 'preview-item';
                        div.innerHTML = `
                            <img src="${e.target.result}" alt="${file.name}">
                            <button class="preview-remove" data-index="${index}">×</button>
                        `;
                        previews.appendChild(div);
                    };
                    reader.readAsDataURL(file);
                });

                submitBtn.style.display = 'block';
                fileInput.value = '';
            }

            previews.addEventListener('click', (e) => {
                if (e.target.classList.contains('preview-remove')) {
                    const index = parseInt(e.target.dataset.index);
                    selectedFiles.splice(index, 1);
                    updatePreviews();
                }
            });

            submitBtn.addEventListener('click', async () => {
                if (!tokenInput.value.trim()) {
                    showStatus('Please enter your upload token', 'error');
                    return;
                }

                if (selectedFiles.length === 0) {
                    showStatus('No files selected', 'error');
                    return;
                }

                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('files', file);
                });

                try {
                    submitBtn.disabled = true;
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
                        selectedFiles = [];
                        updatePreviews();
                    } else {
                        showStatus(`❌ Error: ${result.detail}`, 'error');
                    }
                } catch (error) {
                    showStatus(`❌ Upload failed: ${error.message}`, 'error');
                } finally {
                    submitBtn.disabled = false;
                }
            });

            function showStatus(message, type) {
                status.textContent = message;
                status.className = `status ${type}`;
                status.style.display = 'block';
                setTimeout(() => status.style.display = 'none', 5000);
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
    
    uvicorn.run(app, host="0.0.0.0", port=8766)