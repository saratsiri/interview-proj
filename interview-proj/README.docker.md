# Docker Deployment Guide

## Quick Start

> **✅ Container Functionality Tested**: Multi-container setup successfully tested on macOS with Docker Desktop.

1. **Clone the repository and set up environment:**
```bash
git clone <repository-url>
cd interview-proj
cp .env.example .env
# Edit .env with your API keys
```

2. **Start both API and UI containers:**
```bash
docker-compose up --build
```

3. **Access the application:**
- **UI (Streamlit)**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Container Architecture

### API Container (Port 8000)
- **Service**: FastAPI backend with Claude integration
- **Endpoints**: Content generation, health checks, documentation
- **Data**: Read-only access to article database
- **Environment**: Requires CLAUDE_API_KEY

### UI Container (Port 8501) 
- **Service**: Streamlit web interface
- **Features**: Minimalistic UI for content generation
- **Connection**: Automatically connects to API container
- **Environment**: Uses API_URL=http://api:8000

## Environment Variables

Create a `.env` file with:
```bash
CLAUDE_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional - not tested
```

## Development vs Production

### Development (docker-compose.yml)
- Uses build context from current directory
- Mounts data/ folder as read-only volume
- Health checks enabled
- Network isolation between containers

### Production Considerations
- Use pre-built images instead of build context
- Implement proper secrets management
- Add reverse proxy (nginx) for SSL termination
- Configure resource limits and auto-scaling
- Set up monitoring and logging

## Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services  
docker-compose down

# Rebuild containers
docker-compose up --build

# Scale UI instances
docker-compose up --scale ui=2
```

## Troubleshooting

**Container fails to start:**
- Check `.env` file exists with valid API keys
- Verify ports 8000 and 8501 are available
- Check Docker daemon is running

**UI can't connect to API:**
- Verify both containers are in same network
- Check API container health: `docker-compose ps`
- View API logs: `docker-compose logs api`

**API returns errors:**
- Check CLAUDE_API_KEY is valid
- Verify data/ folder contains article files
- Check API logs for detailed error messages