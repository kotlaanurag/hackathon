"""
Error Handler Bot - Streamlit UI (Microsoft Teams-style)
Reads PCS bad mapping errors and uses Azure OpenAI + PCS Field Mapping reference
to explain errors, suggest resolutions, and output a scheduled JSON requirement.
"""

import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from bot import get_llm_client, get_chat_response
from prompts.system_prompt import SYSTEM_PROMPT

st.set_page_config(page_title="Error Handler Bot - Teams", page_icon="https://img.icons8.com/color/48/microsoft-teams-2019.png", layout="wide")

# --- Teams-style CSS ---
st.markdown("""
<style>
    /* Main container styling - wider chat area */
    .main .block-container {
        max-width: 1200px;
        padding-top: 80px;
        padding-bottom: 1rem;
    }

    /* Teams-style sidebar - dark navy like Teams left rail */
    [data-testid="stSidebar"] {
        background-color: #2B2B40 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] em,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {
        color: #EDEBE9 !important;
    }
    [data-testid="stSidebar"] code {
        background-color: #3D3D56 !important;
        color: #C8C6C4 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #484868 !important;
    }

    /* Chat message styling - Teams bubble look */
    [data-testid="stChatMessage"] {
        border-radius: 8px !important;
        margin-bottom: 8px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    }

    /* Bot messages - left aligned, light grey */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #E1DFDD !important;
    }

    /* User messages - right aligned, purple tint */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: #E8EBFA !important;
        border: 1px solid #D4D6F0 !important;
    }

    /* Chat input styling */
    [data-testid="stChatInput"] textarea {
        border-radius: 6px !important;
        border: 1px solid #6264A7 !important;
    }

    /* Teams header area - fixed at top, above sidebar */
    .teams-header {
        background-color: #6264A7;
        padding: 12px 20px;
        border-radius: 0;
        margin-bottom: 0;
        display: flex;
        align-items: center;
        gap: 12px;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999999;
        height: 90px;
        box-sizing: border-box;
    }

    /* Hide default Streamlit header so it doesn't overlap */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Push sidebar below the fixed header */
    [data-testid="stSidebar"] {
        margin-top: 60px !important;
        z-index: 999 !important;
    }

    /* Sidebar collapse button below header */
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        top: 70px !important;
        z-index: 9999 !important;
    }

    .teams-header h2 {
        color: white !important;
        margin: 0 !important;
        font-size: 18px !important;
        font-weight: 600 !important;
    }
    .teams-header p {
        color: #D4D4F7 !important;
        margin: 0 !important;
        font-size: 13px !important;
    }

    /* Status indicator */
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    .status-online { background-color: #92C353; }
    .status-error { background-color: #C4314B; }

    /* Button styling */
    .stButton > button {
        background-color: #6264A7 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
    }
    .stButton > button:hover {
        background-color: #4F4FA3 !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #6264A7 !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Teams-style toolbar with bot name ---
st.markdown("""
<div class="teams-header">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:28px;">🤖</span>
        <div>
            <h2>Error Handler Bot</h2>
            <p><span class="status-dot status-online"></span>Online &nbsp;|&nbsp; PCS Field Mapping Error Resolution</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def load_error_logs() -> str:
    """Load and format the error logs CSV."""
    csv_path = os.path.join(os.path.dirname(__file__), "configs", "pcs_bad_mapping_error_logs.csv")
    df = pd.read_csv(csv_path)
    return df.to_string(index=False)


def load_field_mapping() -> str:
    """Load and format the PCS Field Mapping reference."""
    xlsx_path = os.path.join(os.path.dirname(__file__), "configs", "PCS FIELD MAPPING.xlsx")
    df = pd.read_excel(xlsx_path)
    # Keep only relevant rows (non-null IRIS Field)
    df_clean = df[df["IRIS Field"].notna()][
        ["IRIS Field", "PCS Payload", "Delivery Phase", "IRIS Dictionary", "Type", "EVERVIEW UI Field", "IRIS UI Field"]
    ]
    return df_clean.to_string(index=False)


# --- Session State Initialization ---
if "messages" not in st.session_state:
    error_logs = load_error_logs()
    field_mapping = load_field_mapping()

    # Extract session ID from the log
    error_df = pd.read_csv(os.path.join(os.path.dirname(__file__), "configs", "pcs_bad_mapping_error_logs.csv"))
    import re
    _ids = set()
    for msg in error_df["Log message"].dropna():
        match = re.search(r"<([a-f0-9]+)>", msg)
        if match:
            _ids.add(match.group(1))
    session_id = list(_ids)[0][:8] if _ids else "unknown"
    user_id = "Sarah Mitchell"

    context_message = (
        f"The following request was made by User: '{user_id}'.\n"
        f"Session ID: {session_id}\n\n"
        f"The request failed with the following errors:\n\n"
        f"```\n{error_logs}\n```\n\n"
        f"Here is the PCS FIELD MAPPING reference:\n\n"
        f"```\n{field_mapping}\n```\n\n"
        f"Present the session ID and explain that the request failed, then walk through each error with explanation and resolution options."
    )

    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context_message},
    ]
    st.session_state.chat_history = []
    st.session_state.finalized = False
    st.session_state.output_json = None

if "client" not in st.session_state:
    st.session_state.client = get_llm_client()

# --- Sidebar with request context (Teams-style channel info) ---
with st.sidebar:
    st.markdown("### 💬 Chat Details")
    st.markdown("---")
    st.markdown("**👤 User**")
    st.markdown("Sarah Mitchell")
    st.markdown("")
    st.markdown("**📌 Session ID**")
    error_df = pd.read_csv(os.path.join(os.path.dirname(__file__), "configs", "pcs_bad_mapping_error_logs.csv"))
    import re as _re
    _task_ids = set()
    for _msg in error_df["Log message"].dropna():
        _m = _re.search(r"<([a-f0-9]+)>", _msg)
        if _m:
            _task_ids.add(_m.group(1))
    # Use first 8 chars of first task ID as session ID
    session_id = list(_task_ids)[0][:8] if _task_ids else "unknown"
    st.markdown(session_id)
    st.markdown("")
    st.markdown("**🕐 Timestamp**")
    st.markdown(f"{error_df['timestamp'].iloc[0]}")
    st.markdown("")
    st.markdown("**⚡ Status**")
    st.markdown("🔴 **Failed**")
    st.markdown("---")
    st.markdown("_Powered by Azure OpenAI_")

# --- Display Chat History ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Generate initial analysis if conversation just started ---
if not st.session_state.chat_history and not st.session_state.finalized:
    with st.chat_message("assistant"):
        with st.spinner("Analyzing request failures..."):
            reply = get_chat_response(st.session_state.client, st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.rerun()

# --- Handle Finalized State ---
if st.session_state.finalized:
    st.success("✅ Requirements finalized and scheduled!")
    st.json(st.session_state.output_json)

    # Download button
    json_str = json.dumps(st.session_state.output_json, indent=2)
    st.download_button(
        label="📥 Download JSON",
        data=json_str,
        file_name=f"requirement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )

    if st.button("🔄 Start New Conversation"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.stop()

# --- Chat Input ---
if user_input := st.chat_input("Type your message..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # Get LLM response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = get_chat_response(st.session_state.client, st.session_state.messages)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # Check if finalized
    if "FINALIZED_JSON:" in reply:
        try:
            json_str = reply.split("FINALIZED_JSON:")[1].strip()
            output = json.loads(json_str)

            # Save to file
            output_dir = os.path.join(os.path.dirname(__file__), "output")
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(output_dir, f"requirement_{timestamp}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)

            st.session_state.output_json = output
            st.session_state.finalized = True
            st.session_state.chat_history.append(
                {"role": "assistant", "content": f"✅ Requirements finalized and saved to `{filepath}`"}
            )
        except (json.JSONDecodeError, IndexError):
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
    else:
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    st.rerun()
