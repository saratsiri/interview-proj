"""Streamlit demo application"""
import streamlit as st
import requests
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Jenosize Trend Generator",
    page_icon="📝",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { padding-top: 2rem; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        width: 100%;
    }
    .generated-content {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🚀 Jenosize Trend Articles Generator")
st.markdown("Generate high-quality business trend articles powered by AI")

# Sidebar
st.sidebar.header("⚙️ Configuration")
api_url = st.sidebar.text_input(
    "API Endpoint",
    value="http://localhost:8008",
    help="Enter the API endpoint URL"
)

# Test API connection
try:
    health_response = requests.get(f"{api_url}/health", timeout=5)
    if health_response.status_code == 200:
        health_data = health_response.json()
        st.sidebar.success(f"✅ API Connected ({health_data.get('generator_type', 'unknown')} mode)")
    else:
        st.sidebar.error("❌ API Connection Failed")
except:
    st.sidebar.error("❌ Cannot reach API")

# Main content
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📋 Article Parameters")
    
    topic = st.text_input(
        "Topic *",
        placeholder="e.g., AI in Healthcare",
        help="Main topic for the article"
    )
    
    category = st.selectbox(
        "Category *",
        ["Technology", "Business", "Healthcare", "Finance", "Marketing", "Science", "Education"]
    )
    
    keywords_input = st.text_area(
        "Keywords * (one per line)",
        placeholder="AI\nhealthcare\ninnovation\nautomation",
        height=120,
        help="SEO keywords to include in the article"
    )
    
    with st.expander("🎯 Advanced Options"):
        target_audience = st.text_input(
            "Target Audience",
            value="Business Leaders and Tech Professionals"
        )
        
        tone = st.selectbox(
            "Tone",
            ["Professional and Insightful", "Casual and Engaging", 
             "Technical and Detailed", "Inspirational"]
        )
    
    generate_button = st.button("🎯 Generate Article", type="primary")

with col2:
    if generate_button:
        if not topic or not keywords_input:
            st.error("❗ Please provide both topic and keywords!")
        else:
            keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]
            
            if len(keywords) > 10:
                st.warning("⚠️ Using first 10 keywords only")
                keywords = keywords[:10]
            
            with st.spinner("🔄 Generating article... This may take a moment."):
                try:
                    # Prepare request
                    request_data = {
                        "topic": topic,
                        "category": category,
                        "keywords": keywords,
                        "target_audience": target_audience,
                        "tone": tone
                    }
                    
                    # Make API request
                    response = requests.post(
                        f"{api_url}/generate",
                        json=request_data,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.header("📄 Generated Article")
                        
                        # Title
                        st.markdown(f"## {result['title']}")
                        
                        # Metadata cards
                        meta_cols = st.columns(4)
                        with meta_cols[0]:
                            st.markdown(f"**📂 Category:** {result['metadata']['category']}")
                        with meta_cols[1]:
                            st.markdown(f"**📊 Words:** {result['metadata']['word_count']}")
                        with meta_cols[2]:
                            st.markdown(f"**🤖 Model:** {result['metadata']['model'][:20]}...")
                        with meta_cols[3]:
                            st.markdown(f"**⏰ Generated:** {datetime.now().strftime('%H:%M:%S')}")
                        
                        st.markdown("---")
                        
                        # Content (fix newline display)
                        st.markdown('<div class="generated-content">', unsafe_allow_html=True)
                        # Replace literal \n\n with actual line breaks
                        clean_content = result['content'].replace('\\n\\n', '\n\n').replace('\\n', '\n')
                        st.markdown(clean_content)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Additional info
                        st.markdown("---")
                        
                        info_cols = st.columns(2)
                        with info_cols[0]:
                            st.markdown("**🎯 Target Audience:** " + result['metadata']['target_audience'])
                            st.markdown("**🎨 Tone:** " + result['metadata']['tone'])
                        with info_cols[1]:
                            st.markdown("**🔑 Keywords:** " + ", ".join(result['metadata']['keywords']))
                            st.markdown("**📅 Generated:** " + result['metadata']['generated_at'][:19].replace('T', ' '))
                        
                        # Download button
                        article_text = f"""# {result['title']}

{result['content']}

---
**Metadata:**
- Category: {result['metadata']['category']}
- Target Audience: {result['metadata']['target_audience']}
- Tone: {result['metadata']['tone']}
- Keywords: {', '.join(result['metadata']['keywords'])}
- Word Count: {result['metadata']['word_count']}
- Generated: {result['metadata']['generated_at']}
- Model: {result['metadata']['model']}
"""
                        
                        st.download_button(
                            label="📥 Download Article (Markdown)",
                            data=article_text,
                            file_name=f"jenosize_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown"
                        )
                        
                        # JSON download
                        st.download_button(
                            label="📥 Download JSON",
                            data=json.dumps(result, indent=2),
                            file_name=f"jenosize_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    else:
                        st.error(f"❌ Error {response.status_code}")
                        try:
                            error_detail = response.json()
                            st.error(f"Details: {error_detail.get('detail', 'Unknown error')}")
                        except:
                            st.error(f"Response: {response.text}")
                
                except requests.exceptions.ConnectionError:
                    st.error("🔗 Cannot connect to API. Make sure the API server is running.")
                    st.info("💡 Start the API with: `python -m uvicorn src.api.main:app --reload`")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. The AI model might be loading. Please try again.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
    else:
        # Instructions
        st.info("👈 Enter article parameters and click 'Generate Article' to create content")
        
        with st.expander("📖 How to use this demo"):
            st.markdown("""
            ### 🚀 Getting Started
            1. **Enter a topic**: Be specific about what you want to write about
            2. **Select a category**: Choose the most relevant business category  
            3. **Add keywords**: Include SEO keywords (one per line, max 10)
            4. **Configure options**: Set target audience and tone in Advanced Options
            5. **Generate**: Click the button and wait for your article
            6. **Download**: Save the generated article for further use
            
            ### 💡 Tips for Better Results
            - **Be Specific**: Use focused topics like "AI in Healthcare" rather than just "AI"
            - **Relevant Keywords**: Include 3-7 keywords that relate to your topic
            - **Right Category**: Choose the category that best fits your topic
            - **Know Your Audience**: Specify who will read this article
            
            ### 📊 Features
            - **Professional Content**: High-quality, business-focused articles
            - **SEO Optimized**: Incorporates your keywords naturally
            - **Multiple Formats**: Download as Markdown or JSON
            - **Real-time Generation**: Get articles in under 30 seconds
            - **Customizable**: Adjust tone and audience for your needs
            """)
        
        # Sample topics
        with st.expander("💡 Sample Topics & Keywords"):
            samples = {
                "AI in Supply Chain Management": ["AI", "logistics", "automation", "efficiency"],
                "Sustainable Business Practices": ["sustainability", "ESG", "green business", "environment"],
                "Digital Transformation in Finance": ["fintech", "digital banking", "blockchain", "innovation"],
                "Remote Work Technology Solutions": ["remote work", "collaboration", "productivity", "cloud"],
                "Cybersecurity for Small Businesses": ["cybersecurity", "data protection", "small business", "threats"]
            }
            
            for sample_topic, sample_keywords in samples.items():
                if st.button(f"📝 Use: {sample_topic}", key=sample_topic):
                    st.session_state.topic = sample_topic
                    st.session_state.keywords = "\n".join(sample_keywords)

# Footer
st.markdown("---")
st.markdown("**🏢 Jenosize Trend Articles Generator** | Built with ❤️ using FastAPI & Streamlit")

# Add some usage statistics in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Quick Stats")
st.sidebar.info("""
**Features:**
- ⚡ Fast generation (< 30s)
- 🎯 SEO optimized content  
- 📱 Mobile-friendly interface
- 💾 Multiple download formats
- 🔄 Real-time API status
""")

# API documentation link
st.sidebar.markdown("### 🔗 API Documentation")
st.sidebar.markdown(f"[📚 Interactive Docs]({api_url}/docs)")
st.sidebar.markdown(f"[📖 ReDoc]({api_url}/redoc)")