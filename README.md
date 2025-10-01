# 📸 Vibe Screenshots

A beautiful screenshot gallery with web upload functionality. Display your screenshots in a randomized, collision-free layout and upload new ones from any device.

## Features

- 🖼️ **Beautiful Gallery**: Auto-arranging screenshot display with smart collision detection
- 📱 **Mobile Upload**: Responsive web interface for uploading from phone/laptop
- 🔄 **Auto-Refresh**: Gallery updates automatically when new images are uploaded
- 🔐 **Secure**: Token-based authentication for uploads
- 🖼️ **Multi-Format**: Supports JPG, PNG, HEIC, GIF, WebP
- 📐 **Smart Resizing**: Automatic image sizing for optimal display

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start development servers:**
   ```bash
   ./start_dev.sh
   ```
   
   Or use the Python version:
   ```bash
   python start_servers.py
   ```

3. **Access your apps:**
   - 📸 **Gallery**: http://localhost:8000
   - 📤 **Upload**: http://localhost:8001
   - 🔑 **Token**: `dev-token-123` (default)

## Production Deployment

1. **Set secure token:**
   ```bash
   export UPLOAD_TOKEN="your-super-secret-token"
   ```

2. **Run servers:**
   ```bash
   # Gallery server
   cd source && python -m http.server 8000
   
   # Upload server  
   python upload_app.py
   ```

3. **Configure reverse proxy** (nginx/apache) to serve both:
   - Gallery: `domain.com` → `localhost:8000`
   - Upload: `domain.com/upload` → `localhost:8001`

## How It Works

1. **Gallery** (`source/`): Displays screenshots in a randomized layout
2. **Upload App** (`upload_app.py`): FastAPI server for secure file uploads
3. **Auto-Integration**: Uploads trigger automatic gallery refresh

## File Structure

```
├── source/
│   ├── index.html          # Gallery interface
│   ├── lister.py          # Generates image metadata
│   └── [your-images]      # Screenshot files
├── upload_app.py          # Upload server
├── start_dev.sh           # Development server script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Development

- **Auto-reload**: Uses `watchdog` for automatic server restart on code changes
- **Hot reload**: Upload server restarts when Python files change
- **Port management**: Automatically kills processes on ports 8000/8001

## Security Notes

- Change `UPLOAD_TOKEN` for production use
- Configure CORS origins in `upload_app.py` for your domain
- Consider adding rate limiting for public deployments

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Test with `./start_dev.sh`
5. Submit a pull request

---

Built with ❤️ using FastAPI and vanilla JS