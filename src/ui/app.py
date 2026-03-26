import streamlit as st
import requests
import os
import uuid
import re

# Configuration
API_URL = os.getenv("TOOLOO_API_URL", "http://localhost:8002")

# Page Config
st.set_page_config(
    page_title="TooLoo V2 - Governance Dashboard",
    page_icon="🤖",
    layout="wide"
)

# Initialize Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = f"s-{uuid.uuid4().hex[:12]}"
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helper Functions ---
def check_health():
    try:
        response = requests.get(f"{API_URL}/v2/health", timeout=2)
        return response.ok, response.json() if response.ok else None
    except requests.RequestException:
        return False, None

def send_chat_message(text: str, depth_level: int = 1):
    try:
        payload = {
            "text": text,
            "session_id": st.session_state.session_id,
            "depth_level": depth_level
        }
        res = requests.post(f"{API_URL}/v2/buddy/chat", json=payload, timeout=30)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        st.error(f"Error communicating with API: {e}")
        return None

def render_chat_content(content: str):
    """Parses custom tags like <mermaid_diagram> and renders them in Streamlit."""
    mermaid_pattern = re.compile(
        r'<(?:mermaid_diagram|visual_artifact)[^>]*?(?:title="([^"]+)")?[^>]*>([\s\S]*?)<\/(?:mermaid_diagram|visual_artifact)>'
    )
    last_end = 0
    
    for match in mermaid_pattern.finditer(content):
        # Render text before the diagram
        text_before = content[last_end:match.start()].strip()
        if text_before:
            st.markdown(text_before)
            
        # Render the diagram
        title = match.group(1) or "Diagram"
        diagram_code = match.group(2).strip()
        
        if diagram_code.startswith("mermaid "):
            diagram_code = diagram_code[8:].strip()
        
        st.markdown(f"**{title}**")
        st.markdown(f"```mermaid\n{diagram_code}\n```")
        
        last_end = match.end()
        
    # Render any remaining text
    text_after = content[last_end:].strip()
    if text_after:
        st.markdown(text_after)

# --- UI Sidebar ---
with st.sidebar:
    st.title("TooLoo V2 Settings")
    
    # Status Indicator
    is_healthy, health_data = check_health()
    if is_healthy:
        st.success("API Status: ONLINE 🟢")
        if health_data:
            st.caption(f"Router: {health_data['components'].get('router')}")
            st.caption(f"Psyche Bank: {health_data['components'].get('psyche_bank')}")
    else:
        st.error("API Status: OFFLINE 🔴")

    st.markdown("---")
    depth_level = st.slider("Deep Cognition Level", min_value=1, max_value=2, value=1, 
                            help="1 = Chat/Explore, 2 = JIT Validation (deeper signals)")

    uploaded_file = st.file_uploader("Upload Context File", type=["txt", "json", "md", "csv"])
    if uploaded_file:
        st.info(f"Loaded: {uploaded_file.name}")
        # Next steps: Hook up file processing to the API if needed
        
    st.markdown("---")
    if st.button("Reset Session Context"):
        st.session_state.messages = []
        st.session_state.session_id = f"s-{uuid.uuid4().hex[:12]}"
        st.rerun()

# --- Main App ---
st.title("TooLoo V2 Cognitive Interface")
st.markdown("A decoupled, human-in-the-loop dashboard governing the structural AI engine.")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_chat_content(msg["content"])
        else:
            st.markdown(msg["content"])
        
        # Display metadata if present for AI responses
        if msg["role"] == "assistant" and "metadata" in msg:
            meta = msg["metadata"]
            with st.expander("Cognitive Telemetry"):
                if "intent" in meta:
                    st.write(f"**Intent**: {meta['intent']} (Confidence: {meta.get('confidence', 0):.2f})")
                if "emotional_state" in meta:
                    st.write(f"**Emotional State**: {meta['emotional_state']}")
                if "latency_ms" in meta:
                    st.write(f"**Latency**: {meta['latency_ms']} ms")
                if "tribunal_passed" in meta:
                    st.write(f"**Tribunal Passed**: {meta['tribunal_passed']}")

# Chat Input
if prompt := st.chat_input("Enter your mandate or inquiry..."):
    # Append User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API and get response
    with st.chat_message("assistant"):
        with st.spinner("Processing in TooLoo Engine..."):
            result = send_chat_message(prompt, depth_level)
            
            if result:
                response_text = result.get("response", "No response text provided.")
                render_chat_content(response_text)
                
                # Append Assistant Message with telemetry metadata
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "metadata": {
                        "intent": result.get("intent"),
                        "confidence": result.get("confidence"),
                        "emotional_state": result.get("emotional_state"),
                        "latency_ms": result.get("latency_ms"),
                        "tribunal_passed": result.get("tribunal_passed")
                    }
                })
                st.rerun()
