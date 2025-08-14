"""Streamlit demo application"""
import streamlit as st
import requests
import json
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Jenosize Trend Generator",
    page_icon="📝",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        width: 100%;
        height: 3rem;
        border-radius: 8px;
    }
    .generated-content {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📝 Jenosize Trend Generator")

# API configuration (minimal sidebar)
with st.sidebar:
    api_url = st.text_input("API Endpoint", value=os.getenv("API_URL", "http://localhost:8000"))
    # Simple connection status
    try:
        health_response = requests.get(f"{api_url}/health", timeout=3)
        if health_response.status_code == 200:
            st.success("✅ Connected")
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ No Connection")

# Main form
with st.form("article_form"):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        topic = st.text_input(
            "Topic *",
            placeholder="e.g., AI in Healthcare"
        )
        
        category = st.selectbox(
            "Category *",
            ["Consumer Insights", "Experience", "Futurist", "Marketing", "Technology", 
             "Utility Consumer Insights Sustainability"]
        )
        
        keywords_input = st.text_area(
            "Keywords (one per line) *",
            placeholder="AI\nhealthcare\nautomation",
            height=100
        )
    
    with col2:
        target_audience = st.selectbox(
            "Target Audience",
            ["Business Leaders", "Tech Professionals", "Healthcare Professionals", 
             "Marketing Professionals", "C-Suite Executives", "SME Owners", 
             "Startup Founders", "Digital Marketers"]
        )
        
        content_length = st.selectbox(
            "Content Length",
            ["Short", "Medium", "Long", "Comprehensive"],
            index=1
        )
        
        industry = st.text_input(
            "Industry Focus",
            placeholder="e.g., Healthcare, Fintech"
        )
    
    # Advanced options (collapsed by default)
    with st.expander("Advanced Options"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            tone = st.selectbox(
                "Tone",
                ["Professional and Insightful", "Casual and Engaging", 
                 "Technical and Detailed", "Inspirational"]
            )
            
            include_statistics = st.checkbox("Include Statistics", value=True)
            
            use_style_matching = st.checkbox("Use Style Matching", value=True)
        
        with col_b:
            call_to_action_type = st.selectbox(
                "Call-to-Action",
                ["consultation", "contact", "demo", "whitepaper", "newsletter", "none"]
            )
            
            include_case_studies = st.checkbox("Include Case Studies", value=True)
            
            if use_style_matching:
                num_style_examples = st.slider("Style Examples", 1, 5, 3)
            else:
                num_style_examples = 3
    
    # Generate button
    submitted = st.form_submit_button("Generate Article", type="primary")

# Generation logic
if submitted:
    if not topic or not keywords_input:
        st.error("Please provide both topic and keywords")
    else:
        keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]
        
        if len(keywords) > 10:
            st.warning("Using first 10 keywords only")
            keywords = keywords[:10]
        
        with st.spinner("Generating article..."):
            try:
                request_data = {
                    "topic": topic,
                    "category": category,
                    "keywords": keywords,
                    "target_audience": target_audience,
                    "tone": tone,
                    "industry": industry if industry else None,
                    "content_length": content_length,
                    "include_statistics": include_statistics,
                    "include_case_studies": include_case_studies,
                    "call_to_action_type": call_to_action_type,
                    "use_style_matching": use_style_matching,
                    "num_style_examples": num_style_examples
                }
                
                response = requests.post(
                    f"{api_url}/generate",
                    json=request_data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results - extract proper title
                    title = result['title']
                    if len(title) > 100:  # If title is too long, create a shorter one
                        title = f"{topic} - {result['metadata']['category']}"
                    
                    st.markdown(f"## {title}")
                    
                    # Simple metadata
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**Category**")
                        st.write(result['metadata']['category'])
                    with col2:
                        st.metric("Words", result['metadata']['word_count'])
                    with col3:
                        st.metric("Model", result['metadata']['model'].title())
                    
                    # Content
                    clean_content = result['content'].replace('\\\\n\\\\n', '\n\n').replace('\\\\n', '\n')
                    st.markdown(clean_content)
                    
                    # Download options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        article_text = f"""# {result['title']}\n\n{result['content']}\n\n---\n**Generated by Jenosize Trend Generator**\n- Category: {result['metadata']['category']}\n- Keywords: {', '.join(result['metadata']['keywords'])}\n- Words: {result['metadata']['word_count']}"""
                        
                        st.download_button(
                            "📥 Download Markdown",
                            data=article_text,
                            file_name=f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown"
                        )
                    
                    with col2:
                        st.download_button(
                            "📥 Download JSON",
                            data=json.dumps(result, indent=2),
                            file_name=f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    
                    # Style matching info (if used)
                    if result.get('style_matching', {}).get('used_style_examples'):
                        st.success(f"✅ Generated using {len(result['style_matching']['similar_articles'])} style examples")
                
                else:
                    st.error(f"Generation failed: {response.status_code}")
                    try:
                        error_detail = response.json()
                        st.error(f"Details: {error_detail.get('detail', 'Unknown error')}")
                    except:
                        st.error(f"Response: {response.text}")
            
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API. Make sure the server is running.")
            except requests.exceptions.Timeout:
                st.error("Request timed out. Please try again.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")