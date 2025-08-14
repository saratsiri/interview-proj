# Render.com Deployment Guide

## Overview

This project uses Render's Blueprint feature to deploy a multi-service architecture with:
- **FastAPI Backend** (`jenosize-api`): Content generation API with Claude integration
- **Streamlit Frontend** (`jenosize-ui`): Web interface for content creation

## Prerequisites

1. **GitHub Repository**: Project must be in a GitHub repository
2. **Render Account**: Create account at [render.com](https://render.com)
3. **API Keys**: Claude API key (required), OpenAI API key (optional)

## Deployment Steps

### 1. Prepare Repository

Ensure these files are in your repository root:
- `render.yaml` - Blueprint configuration
- `requirements.txt` - Python dependencies
- `start-api.sh` - API startup script
- `start-ui.sh` - UI startup script
- `.streamlit/config.toml` - Streamlit configuration

### 2. Deploy to Render

#### Option A: Blueprint Deployment (Recommended)

1. **Connect Repository**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository containing your project

2. **Configure Environment Variables**:
   - **For jenosize-api service**:
     - `CLAUDE_API_KEY`: Your Claude API key (required)
     - `OPENAI_API_KEY`: Your OpenAI API key (optional)
   - Environment variables are configured automatically through the blueprint

3. **Deploy**:
   - Click "Apply Blueprint"
   - Render will create and deploy both services automatically
   - Deployment typically takes 5-10 minutes

#### Option B: Manual Service Creation

If you prefer manual setup:

1. **Create API Service**:
   - Service Type: Web Service
   - Repository: Your GitHub repo
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `./start-api.sh`

2. **Create UI Service**:
   - Service Type: Web Service  
   - Repository: Your GitHub repo
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `./start-ui.sh`
   - Environment Variable: `API_URL` = `[API-Service-URL]`

### 3. Access Your Application

After successful deployment:
- **API Service**: `https://jenosize-api.onrender.com`
- **UI Service**: `https://jenosize-ui.onrender.com`
- **API Documentation**: `https://jenosize-api.onrender.com/docs`

## Architecture Details

### Service Communication

- **Backend → Frontend**: Automatic via `fromService` in render.yaml
- **Environment Variables**: Render automatically injects service URLs
- **Health Checks**: Both services include health endpoints
- **CORS**: Configured to allow frontend → backend communication

### Resource Allocation

- **Plan**: Free tier (sufficient for development/testing)
- **Scaling**: Manual scaling available through dashboard
- **Monitoring**: Built-in logs and metrics in Render dashboard

## Configuration Files

### render.yaml
```yaml
services:
  - type: web
    name: jenosize-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: ./start-api.sh
    
  - type: web
    name: jenosize-ui
    buildCommand: pip install -r requirements.txt
    startCommand: ./start-ui.sh
```

### Environment Variables

**jenosize-api**:
- `CLAUDE_API_KEY`: Claude API authentication
- `OPENAI_API_KEY`: OpenAI API authentication (backup)
- `ENVIRONMENT`: Set to "production"
- `PYTHONPATH`: Python module path configuration

**jenosize-ui**:
- `API_URL`: Automatically set to API service URL
- `ENVIRONMENT`: Set to "production"

## Monitoring & Troubleshooting

### Logs
- Access logs through Render dashboard
- Each service has separate log streams
- Real-time log streaming available

### Health Checks
- API: `GET /health`
- UI: Streamlit built-in health endpoint
- Both services include startup logging

### Common Issues

1. **Build Failures**:
   - Check `requirements.txt` dependencies
   - Verify Python version compatibility
   - Review build logs in dashboard

2. **Service Communication**:
   - Ensure `API_URL` environment variable is set
   - Check CORS configuration in API
   - Verify service names match render.yaml

3. **API Key Issues**:
   - Verify environment variables are set correctly
   - Check API key validity
   - Review API service logs for authentication errors

### Performance Optimization

- **Free Tier Limitations**: Services sleep after 15 minutes of inactivity
- **Scaling**: Upgrade to paid plans for always-on services
- **Caching**: Consider Redis addon for session caching

## Continuous Deployment

- **Auto-Deploy**: Enabled by default on main branch
- **Branch Deployments**: Configure additional branches if needed
- **Rollbacks**: Available through dashboard
- **Preview Deployments**: Automatic for pull requests

## Security Considerations

- Environment variables are encrypted at rest
- HTTPS enabled by default for all services
- Rate limiting configured in API
- Input sanitization implemented
- Audit logging enabled

## Cost Estimation

**Free Tier** (Current Configuration):
- 2 web services × $0/month = $0/month
- 750 hours/month included
- Services sleep when inactive

**Paid Tier** (Production Ready):
- 2 web services × $7/month = $14/month
- Always-on services
- Custom domains available
- Enhanced monitoring

## Support & Resources

- [Render Documentation](https://render.com/docs)
- [Blueprint Reference](https://render.com/docs/blueprint-spec)
- [FastAPI on Render](https://render.com/docs/deploy-fastapi)
- [Streamlit Deployment Guide](https://docs.streamlit.io/knowledge-base/tutorials/deploy)

## Upgrade Path

For production deployment consider:
1. **Paid Plans**: Always-on services, better performance
2. **Custom Domains**: Professional URLs
3. **Database**: PostgreSQL addon for data persistence
4. **Redis**: Caching layer for improved performance
5. **Background Workers**: For async content processing