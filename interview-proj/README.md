# Jenosize Trend Articles Generator

An AI-powered system that generates high-quality business trend articles using language models, designed for Jenosize.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository (if from git)
git clone <repository-url>
cd jenosize-trend-generator

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the API

```bash
# Start the API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python -c "from src.api.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
```

The API will be available at: http://localhost:8000

### 3. Run the Demo

```bash
# In a new terminal (with venv activated)
streamlit run demo/app.py
```

The demo will be available at: http://localhost:8501

## 📖 API Documentation

Once the API is running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## 🔥 Features

- **🤖 AI-Powered Generation**: Uses advanced language models for high-quality content
- **📱 Interactive Demo**: Beautiful Streamlit interface for easy testing
- **⚡ Fast & Reliable**: Optimized for quick response times
- **🎯 SEO Optimized**: Incorporates keywords naturally into content
- **📊 Rich Metadata**: Detailed information about generated articles
- **🔄 Fallback System**: Works with or without AI models installed
- **📥 Multiple Formats**: Download articles as Markdown or JSON
- **🌐 CORS Enabled**: Ready for web integration

## 📊 Project Structure

```
jenosize-trend-generator/
├── src/                    # Source code
│   ├── api/               # FastAPI application
│   │   ├── main.py       # Main API app
│   │   └── schemas.py    # Request/response models
│   ├── model/            # AI model and generation
│   │   ├── config.py     # Model configuration
│   │   └── generator.py  # Article generation logic
│   ├── data/             # Data processing (future)
│   │   └── scraper.py    # Sample data creation
│   └── utils/            # Utilities (future)
├── demo/                  # Streamlit demo application
│   └── app.py            # Demo interface
├── tests/                # Test suite (future)
├── data/                 # Data storage
│   ├── raw/             # Raw training data
│   └── processed/       # Processed data
├── models/               # Model storage
│   └── checkpoints/     # Saved models
├── deployment/          # Deployment configs
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.9+
- **AI/ML**: Transformers, PyTorch (optional)
- **Frontend Demo**: Streamlit
- **Data**: Pandas, JSON
- **Deployment**: Docker, Uvicorn

## 📝 API Usage Examples

### Generate Article (cURL)

```bash
curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "AI in Healthcare",
       "category": "Technology", 
       "keywords": ["AI", "healthcare", "innovation", "automation"],
       "target_audience": "Healthcare Executives",
       "tone": "Professional and Insightful"
     }'
```

### Generate Article (Python)

```python
import requests

response = requests.post("http://localhost:8000/generate", json={
    "topic": "Sustainable Business Practices",
    "category": "Sustainability",
    "keywords": ["sustainability", "ESG", "green business"],
    "target_audience": "Business Leaders",
    "tone": "Professional and Insightful"
})

article = response.json()
print(f"Title: {article['title']}")
print(f"Content: {article['content'][:200]}...")
```

## 🚀 Deployment Options

### Option 1: Render.com (Recommended)
1. Push code to GitHub
2. Connect to Render.com
3. Deploy as Web Service with:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

### Option 2: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Option 3: Docker
```bash
# Build image
docker build -t jenosize-generator .

# Run container
docker run -p 8000:8000 jenosize-generator
```

### Option 4: Hugging Face Spaces
- Create Gradio Space
- Push code with `gradio` interface
- Automatic deployment

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=src tests/
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file:
```bash
# Model Configuration
MODEL_NAME=gpt2
MAX_LENGTH=512
TEMPERATURE=0.8

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

### Model Options

The system supports multiple generation modes:
- **AI Mode**: Uses transformers library with GPT-2 or custom models
- **Mock Mode**: High-quality template-based generation (no AI dependencies)
- **Hybrid Mode**: Falls back to mock if AI models fail

## 🔧 Development

### Adding New Features

1. **New API Endpoints**: Add to `src/api/main.py`
2. **New Schemas**: Define in `src/api/schemas.py`
3. **Model Changes**: Modify `src/model/generator.py`
4. **Demo Updates**: Edit `demo/app.py`

### Code Style

```bash
# Format code
black src/ demo/ tests/

# Check types
mypy src/

# Lint code
flake8 src/ demo/ tests/
```

## 🐛 Troubleshooting

### Common Issues

1. **API won't start**: Check Python version (3.9+ required)
2. **Import errors**: Activate virtual environment and install requirements
3. **Model loading fails**: System will fallback to mock generator automatically
4. **Demo connection issues**: Ensure API is running on correct port

### Performance Tips

- Use mock generator for faster responses during development
- Consider GPU acceleration for AI model inference
- Implement caching for repeated requests
- Use async processing for batch operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

Proprietary - Jenosize

## 👥 Support

For support and questions:
- 📧 Email: support@jenosize.com
- 📞 Phone: +1-XXX-XXX-XXXX
- 🌐 Website: https://jenosize.com

---

**Built with ❤️ for Jenosize AI & Data Engineering Position**