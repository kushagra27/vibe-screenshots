#!/usr/bin/env python3
"""
Railway-optimized version that serves both gallery and upload on same port
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List
import uuid
import io
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image
import pillow_heif

# Register HEIF opener for iOS photos
pillow_heif.register_heif_opener()

app = FastAPI(title="Vibe Screenshots", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN")
if not UPLOAD_TOKEN:
    print("⚠️  WARNING: UPLOAD_TOKEN environment variable not set!")
    print("   Set it in Railway dashboard under Variables")
    UPLOAD_TOKEN = "demo-token-railway-insecure"

# Paths
SOURCE_DIR = Path("source")
UPLOAD_DIR = SOURCE_DIR

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files for gallery
app.mount("/static", StaticFiles(directory="source"), name="static")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != UPLOAD_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials

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
async def gallery():
    """Serve the dynamic gallery page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>vibe images</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                margin: 0; padding: 20px; 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #f5f5f5;
            }
            #container { position: relative; }
            .upload-link {
                position: fixed; top: 20px; right: 20px; z-index: 1000;
                background: #007bff; color: white; padding: 10px 20px;
                border-radius: 25px; text-decoration: none; font-weight: bold;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }
            .upload-link:hover { background: #0056b3; }
            .loading { text-align: center; padding: 50px; color: #666; }
            .empty-state { 
                text-align: center; padding: 100px 20px; 
                max-width: 500px; margin: 0 auto;
            }
            .empty-state h2 { color: #333; margin-bottom: 10px; }
            .empty-state p { color: #666; margin-bottom: 30px; }
            .upload-btn {
                background: #28a745; color: white; padding: 15px 30px;
                border: none; border-radius: 25px; font-size: 16px;
                text-decoration: none; display: inline-block;
                font-weight: bold;
            }
            .upload-btn:hover { background: #218838; }
        </style>
    </head>
    <body>
        <a href="/upload" class="upload-link">📤 Upload</a>
        <div id="container">
            <div class="loading">🖼️ Loading gallery...</div>
        </div>

        <script>
        function shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }

        async function loadGallery() {
            const container = document.getElementById('container');
            
            try {
                const response = await fetch('/api/images');
                if (!response.ok) throw new Error('Failed to load images');
                
                const data = await response.json();
                
                if (data.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <h2>📸 No Screenshots Yet</h2>
                            <p>Your gallery is empty! Start by uploading some screenshots to see them displayed here.</p>
                            <a href="/upload" class="upload-btn">Upload Your First Screenshot</a>
                        </div>
                    `;
                    return;
                }

                // Clear loading message
                container.innerHTML = '';

                let key_values = shuffleArray(data);
                const rect = container.getBoundingClientRect();
                let screen_width = rect.width;

                // Resize images for optimal display
                const pairs = key_values.map(([key, [w, h]]) => {
                    let goal_pixels = 500*300;
                    let actual_pixels = w*h;
                    if (actual_pixels/goal_pixels > 16) {
                        return [parseInt(w/8), parseInt(h/8)];
                    }
                    if (actual_pixels/goal_pixels > 4) {
                        return [parseInt(w/4), parseInt(h/4)];
                    }
                    return [parseInt(w/2), parseInt(h/2)];
                }).map(([w, h]) => [(w+10) > screen_width ? screen_width-10 : w, h]);

                // Gather text nodes for collision detection
                const textNodes = [];
                const treeWalker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    { acceptNode: (node) => node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT }
                );
                while(treeWalker.nextNode()) textNodes.push(treeWalker.currentNode);

                // Place images with collision detection
                let positions = [];
                let i = 0;
                let interval = setInterval(() => {
                    let height = 600;
                    let [w, h] = pairs[i];
                    while (1) {
                        let found_place = false;
                        let w_max = screen_width-w;
                        let h_max = height-h;
                        for (let _ = 0; _ < 50; _++) {
                            let a_left = Math.random() * w_max;
                            let a_top = Math.random() * h_max;
                            let a_right = a_left+w;
                            let a_bottom = a_top+h;

                            // Check intersection with other images
                            let intersects = false;
                            for (let j = 0; j < positions.length; j++) {
                                let [b_left, b_top] = positions[j];
                                let b_right = b_left + pairs[j][0];
                                let b_bottom = b_top + pairs[j][1];
                                if (a_left < b_right && a_right > b_left && a_bottom > b_top && a_top < b_bottom) {
                                    intersects = true;
                                    break;
                                }
                            }

                            // Check intersection with text
                            for (const node of textNodes) {
                                const range = document.createRange();
                                range.selectNodeContents(node);
                                const rect = range.getBoundingClientRect();
                                let node_top = rect.top + window.pageYOffset;
                                let node_left = rect.left + window.pageXOffset;
                                
                                if (a_left < (node_left+rect.width) && a_right > node_left && a_bottom > node_top && a_top < (node_top+rect.height)) {
                                    intersects = true;
                                    break;
                                }
                            }

                            if (!intersects) {
                                found_place = true;
                                positions.push([parseInt(a_left), parseInt(a_top)]);
                                break;
                            }
                        }
                        if (found_place) {
                            break;
                        } else {
                            height += 50;
                        }
                    }

                    // Create the image
                    let img = document.createElement("img");
                    img.src = `/static/${key_values[i][0]}`;
                    img.width = pairs[i][0];
                    img.height = pairs[i][1];
                    img.style.width = pairs[i][0] + 'px';
                    img.style.height = pairs[i][1] + 'px';
                    img.style.position = "absolute";
                    img.style.top = positions[i][1] + 'px';
                    img.style.left = positions[i][0] + 'px';
                    img.loading = "lazy";
                    container.appendChild(img);

                    i++;
                    if (i == key_values.length) {
                        clearInterval(interval);
                    }
                }, 100);

            } catch (error) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h2>❌ Error Loading Gallery</h2>
                        <p>Failed to load images: ${error.message}</p>
                        <a href="/upload" class="upload-btn">Try Uploading</a>
                    </div>
                `;
            }
        }

        // Load gallery when page loads
        loadGallery();
        </script>
    </body>
    </html>
    """

@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Serve the upload interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Screenshots</title>
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
            .upload-btn, .gallery-btn {
                background: #007bff; color: white; border: none;
                padding: 12px 24px; border-radius: 6px; cursor: pointer;
                font-size: 16px; margin: 10px; text-decoration: none;
                display: inline-block;
            }
            .gallery-btn { background: #28a745; }
            .upload-btn:hover { background: #0056b3; }
            .gallery-btn:hover { background: #218838; }
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
            .header { text-align: center; margin-bottom: 20px; }
            @media (max-width: 600px) {
                body { padding: 10px; }
                .upload-area { padding: 20px; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📸 Upload Screenshots</h1>
            <a href="/" class="gallery-btn">🖼️ View Gallery</a>
        </div>
        
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

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const tokenInput = document.getElementById('token');
            const status = document.getElementById('status');

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
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${tokenInput.value}`
                        },
                        body: formData
                    });

                    const result = await response.json();
                    
                    if (response.ok) {
                        showStatus(`✅ Uploaded ${result.uploaded_count} files! Redirecting to gallery...`, 'success');
                        setTimeout(() => window.location.href = '/', 1500);
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

@app.post("/api/upload")
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
                img.verify()
            except Exception:
                errors.append(f"{file.filename}: Invalid or corrupted image")
                continue
            
            # Generate unique filename
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
    
    response = {
        "uploaded_count": len(uploaded_files),
        "uploaded_files": uploaded_files,
        "errors": errors,
        "message": f"Uploaded {len(uploaded_files)} files successfully! Gallery will update automatically."
    }
    
    if errors and not uploaded_files:
        raise HTTPException(status_code=400, detail="All uploads failed")
    
    return response

@app.get("/api/images")
async def list_images():
    """Dynamically list all images with their dimensions"""
    try:
        images = []
        
        # Ensure source directory exists
        SOURCE_DIR.mkdir(exist_ok=True)
        
        # Scan for image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
        
        for file_path in SOURCE_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                try:
                    # Open image to get dimensions
                    with Image.open(file_path) as img:
                        width, height = img.size
                        images.append([file_path.name, [width, height]])
                except Exception as e:
                    # Skip files that can't be opened as images
                    print(f"Skipping {file_path.name}: {e}")
                    continue
        
        return images
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing images: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if source directory exists
        source_exists = SOURCE_DIR.exists()
        
        # Count images
        try:
            images = await list_images()
            image_count = len(images)
        except:
            image_count = 0
            
        return {
            "status": "healthy", 
            "upload_dir": str(UPLOAD_DIR),
            "source_dir_exists": source_exists,
            "upload_token_set": bool(UPLOAD_TOKEN and UPLOAD_TOKEN != "demo-token-railway-insecure"),
            "image_count": image_count
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting on port {port}")
    print(f"🔑 Upload token: {UPLOAD_TOKEN}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)