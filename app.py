import streamlit as st
import pandas as pd
import io
import os
from engine import (
    init_local_db, load_claims_file, get_active_rules, 
    add_rule_to_db, delete_rule_from_db, 
    group_and_validate_claims, cleanup_local_files, 
    get_base_dir, DB_NAME, sqlite3
)

st.set_page_config(
    page_title="Claims Scrubber for UAE", 
    page_icon="->", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Local Database
init_local_db()

# Monochrome Aesthetic: Pure black, dark grays, white, soft dull-gray active tabs, and dark gray buttons
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        background-color: #000000;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Section */
    .app-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.9rem;
        color: #888888;
        margin: 4px 0 0 0;
    }

    /* Monochrome Tabs: Selected tab is a dull, subtle dark gray instead of bright color */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        background-color: #0d0d0d;
        padding: 12px 16px;
        border-radius: 16px;
        border: 1px solid #1f1f1f;
        margin-bottom: 25px;
        margin-top: 15px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #141414;
        border-radius: 12px;
        color: #888888;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0 24px;
        border: 1px solid #222222;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #1c1c1c;
        color: #ffffff;
        border-color: #333333;
    }
    .stTabs [aria-selected="true"] {
        background-color: #262626 !important;
        color: #ffffff !important;
        border-color: #444444 !important;
        box-shadow: none !important;
    }

    /* Clean Rounded Cards with Ample Padding */
    .custom-card {
        background-color: #0d0d0d;
        border: 1px solid #1f1f1f;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 20px;
    }

    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #0d0d0d;
        border: 1px solid #1f1f1f;
        padding: 20px;
        border-radius: 14px;
    }
    div[data-testid="stMetric"] label {
        color: #888888 !important;
        font-weight: 500;
        font-size: 0.9rem;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
        font-size: 1.6rem;
    }

    /* Greyscale Dark Gray Buttons */
    div.stButton > button {
        border-radius: 12px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        background-color: #1f1f1f;
        color: #ffffff;
        border: 1px solid #333333;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #2a2a2a;
        border-color: #555555;
    }

    /* Inputs & Selectboxes */
    .stTextInput input, .stSelectbox select {
        background-color: #141414 !important;
        border: 1px solid #262626 !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        padding: 10px 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Header Section
col_title, col_exit = st.columns([7, 1])
with col_title:
    st.markdown("""
        <div style="padding: 10px 0;">
            <p class="app-title">Claims Scrubber for UAE</p>
            <p class="app-subtitle">Automated offline healthcare claim compilation and coding validation suite</p>
        </div>
    """, unsafe_allow_html=True)

with col_exit:
    st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
    if st.button("[- Exit App]", use_container_width=True, help="Closes app and deletes temporary local files"):
        cleanup_local_files()
        st.success("App closed successfully.")
        os._exit(0)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# Navigation Tabs
tab1, tab2, tab3 = st.tabs([
    "-> Claim Scrubber & Validation", 
    "-> Active Checks & Info", 
    "-> Code Reference Handbook"
])

# ==================== TAB 1: CLAIM SCRUBBER ====================
with tab1:
    st.markdown("""
        <div class="custom-card">
            <h3 style="margin-top: 0; color: #ffffff; font-size: 1.2rem; font-weight: 600;">Upload Claims File</h3>
            <p style="color: #888888; font-size: 0.95rem; margin-bottom: 0; line-height: 1.5;">Select your claims dataset (CSV, Excel, or XML format). The system will group line items by Claim ID and cross-check them against your active validation rules.</p>
        </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Choose claims file", type=["csv", "xlsx", "xls", "xml"])
    
    if uploaded_file is not None:
        try:
            raw_df = load_claims_file(uploaded_file)
            st.markdown(f"<div style='padding: 12px 18px; background-color: #0d0d0d; border: 1px solid #1f1f1f; border-radius: 12px; margin: 15px 0; color: #ffffff; font-weight: 500;'>-> File uploaded successfully. Total line rows loaded: <b>{len(raw_df):,}</b></div>", unsafe_allow_html=True)
            
            st.markdown("<br><h4 style='color: #ffffff; font-weight: 600;'>Column Mapping</h4>", unsafe_allow_html=True)
            columns = list(raw_df.columns)
            c1, c2 = st.columns(2)
            
            with c1:
                claim_col = st.selectbox("Claim ID Column (Required)", columns, index=0)
            with c2:
                code_col = st.selectbox("Diagnosis/Procedure Code Column (Required)", columns, index=min(1, len(columns)-1))
                
            col_map = {'claim_id': claim_col, 'code': code_col}
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("-> Run Claim Validation"):
                rules = get_active_rules()
                flagged_df, grouped_claims = group_and_validate_claims(raw_df, col_map, rules)
                
                st.markdown("<br><h4 style='color: #ffffff; font-weight: 600;'>Validation Results</h4>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Line Rows", f"{len(raw_df):,}")
                m2.metric("Unique Claims Compiled", f"{len(grouped_claims):,}")
                m3.metric("Incorrectly Coded Claims", f"{len(flagged_df):,}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if not flagged_df.empty:
                    # Output error state utilizes red as requested previously
                    st.error(f"Found {len(flagged_df)} claim(s) with invalid coding combinations.")
                    
                    display_df = flagged_df.reset_index(drop=True)
                    display_df.index += 1
                    st.dataframe(display_df, use_container_width=True)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        display_df.to_excel(writer, sheet_name='Incorrectly Coded Claims', index=True)
                        raw_df.to_excel(writer, sheet_name='Original Data', index=False)
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button(
                        label="-> Download Audit Report (Excel)",
                        data=output.getvalue(),
                        file_name="Invalid_Claims_Audit_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.markdown("<div style='padding: 16px; background-color: #0d0d0d; border: 1px solid #333333; border-radius: 12px; color: #ffffff; font-weight: 500; text-align: center;'>All claims passed validation. No invalid coding combinations detected.</div>", unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# ==================== TAB 2: ACTIVE CHECKS & INFO ====================
with tab2:
    st.markdown("""
        <div class="custom-card">
            <h3 style="margin-top: 0; color: #ffffff; font-size: 1.2rem; font-weight: 600;">Active Coding Error Rules</h3>
            <p style="color: #888888; font-size: 0.95rem; margin-bottom: 0; line-height: 1.5;">Manage your active pairwise coding checks or add new error combinations below.</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.expander("+ Add New Coding Error Rule"):
        with st.form("add_rule_form"):
            c1, c2 = st.columns(2)
            with c1:
                r_id = st.text_input("Rule ID (e.g. R011)")
                r_name = st.text_input("Rule Name")
            with c2:
                r_c1 = st.text_input("Code 1 (e.g. E10.9)")
                r_c2 = st.text_input("Code 2 (e.g. E11.9)")
            r_desc = st.text_area("Description / Clinical Reason")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Save Rule"):
                if r_id and r_name and r_c1 and r_c2:
                    add_rule_to_db(r_id, r_name, r_c1, r_c2, r_desc)
                    st.success(f"Rule {r_id} added successfully.")
                    st.rerun()
                else:
                    st.error("Please fill in Rule ID, Name, Code 1, and Code 2.")

    st.markdown("<br>", unsafe_allow_html=True)
    rules = get_active_rules()
    st.markdown(f"<h4 style='color: #ffffff; font-weight: 600;'>Current Active Checks ({len(rules)})</h4>", unsafe_allow_html=True)
    
    for r in rules:
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 2.5, 3.5, 1])
            col1.write(f"**{r['rule_id']}**")
            col2.write(f"**{r['rule_name']}**")
            col3.write(f"Pair: `{r['code_1']} & {r['code_2']}`")
            if col4.button("Delete", key=f"del_{r['rule_id']}"):
                delete_rule_from_db(r['rule_id'])
                st.rerun()
        st.markdown("<hr style='margin: 12px 0px; border-color: #1f1f1f;'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='custom-card'>
        <h3 style="margin-top: 0; color: #ffffff; font-size: 1.1rem; font-weight: 600;">Custom Rules File Format Guide</h3>
        <p style="color: #888888; font-size: 0.9rem; line-height: 1.5;">To add custom coding rules via your local <code>validation_rules.csv</code> file, ensure the first row contains these exact headers:</p>
        <code style="background-color: #000000; padding: 10px 14px; border-radius: 8px; display: block; margin: 12px 0; color: #cccccc; border: 1px solid #222222;">rule_id, rule_name, code_1, code_2, description</code>
        <ul style="color: #888888; font-size: 0.9rem; margin-bottom: 0; line-height: 1.6;">
            <li><b>rule_id:</b> Unique identifier (e.g., R011)</li>
            <li><b>rule_name:</b> Short title of the error check</li>
            <li><b>code_1 & code_2:</b> The two mutually exclusive codes being compared</li>
            <li><b>description:</b> Clinical reason why they cannot be billed together</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ==================== TAB 3: REFERENCE HANDBOOK ====================
with tab3:
    st.markdown("""
        <div class="custom-card">
            <h3 style="margin-top: 0; color: #ffffff; font-size: 1.2rem; font-weight: 600;">ICD & CPT Reference Handbook</h3>
            <p style="color: #888888; font-size: 0.95rem; margin-bottom: 0; line-height: 1.5;">Search through the local reference handbook for code definitions and categories.</p>
        </div>
    """, unsafe_allow_html=True)
    
    search_term = st.text_input("Search code or description (e.g., 'Diabetes', 'E11.9', 'Radiology')", "")
    
    db_path = os.path.join(get_base_dir(), DB_NAME)
    conn = sqlite3.connect(db_path)
    if search_term:
        q = f"%{search_term}%"
        query_df = pd.read_sql_query("SELECT code, code_type, description, category FROM reference_handbook WHERE code LIKE ? OR description LIKE ? OR category LIKE ? LIMIT 500", conn, params=(q, q, q))
    else:
        query_df = pd.read_sql_query("SELECT code, code_type, description, category FROM reference_handbook LIMIT 500", conn)
    conn.close()
    
    query_df = query_df.reset_index(drop=True)
    query_df.index += 1
    
    st.markdown(f"<br><span style='color: #888888;'>Showing <b>{len(query_df):,}</b> reference records:</span><br><br>", unsafe_allow_html=True)
    st.dataframe(query_df, use_container_width=True)
