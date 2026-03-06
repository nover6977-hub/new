import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, date

# --- DATABASE SETUP (GOOGLE SHEETS) ---
# Replace the URL below with your Google Sheet "Share" link
SQL_URL = "https://docs.google.com/spreadsheets/d/1LzNAsp9ztZljukpr79Md1rufRupiQjuKogiqURbsCmM/edit?usp=sharing"

st.set_page_config(page_title="PrintMaster Pro", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=SQL_URL, ttl="0s")

df = load_data()

# Ensure all columns are handled correctly
columns = ["Category", "Printer", "Item", "Spec", "Quantity", "Min_Stock", "Cost", "Buy_Link", "Last_Dried", "Last_Maintenance", "Location"]
df = df.reindex(columns=columns)
df[['Item', 'Spec', 'Printer', 'Location', 'Buy_Link']] = df[['Item', 'Spec', 'Printer', 'Location', 'Buy_Link']].astype(str)

# --- G-CODE PARSER ---
def parse_gcode(file_bytes):
    text = file_bytes.decode("utf-8", errors="ignore")
    patterns = [r"filament used \[g\] = ([\d.]+)", r"total filament used \[g\]: ([\d.]+)", r"filament used: ([\d.]+)g"]
    for p in patterns:
        match = re.search(p, text)
        if match: return float(match.group(1))
    return 0.0

# --- UI STYLING ---
st.markdown("""
    <style>
    * { color: black !important; font-weight: 700 !important; }
    .stApp { background-color: #FFFFFF !important; }
    h1, h3 { color: #D32F2F !important; }
    .stButton>button { background: #1976D2 !important; color: white !important; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 PRINTMASTER PRO: CLOUD EDITION")

# --- 1. G-CODE AUTO-DEDUCT ---
with st.expander("📂 G-CODE AUTO-DEDUCT"):
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        gfile = st.file_uploader("Upload .gcode", type=['gcode'])
        g_weight = parse_gcode(gfile.read()) if gfile else 0.0
    with g_col2:
        fil_opts = (df[df["Category"]=="Filament"]['Item'] + " (" + df[df["Category"]=="Filament"]['Spec'] + ")").tolist()
        target_f = st.selectbox("Deduct From", fil_opts if fil_opts else ["No Stock"])
        if st.button("🔥 Deduct Weight") and g_weight > 0:
            f_name = target_f.split(" (")[0]
            df.loc[df["Item"] == f_name, "Quantity"] -= g_weight
            conn.update(spreadsheet=SQL_URL, data=df)
            st.cache_data.clear()
            st.rerun()

# --- 2. ADD SECTIONS ---
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🧶 Add Filament")
    f_n = st.text_input("Material", key="fn")
    f_s = st.text_input("Color", key="fs")
    f_q = st.number_input("Weight (g)", min_value=0, key="fq")
    f_p = st.number_input("Price (£)", min_value=0.0, key="fp")
    f_link = st.text_input("Buy Link", key="flink")
    if st.button("➕ Add Spool"):
        new_row = pd.DataFrame([["Filament", "Global", str(f_n), str(f_s), f_q, 200, f_p, str(f_link), str(date.today()), "N/A", ""]], columns=columns)
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=SQL_URL, data=df)
        st.cache_data.clear()
        st.rerun()

with c2:
    st.markdown("### 🛠️ Add Printer or Part")
    p_list = sorted(df[df["Printer"] != "Global"]["Printer"].unique().tolist())
    p_sel = st.selectbox("Assign to...", ["🆕 REGISTER NEW PRINTER"] + p_list)
    is_new = p_sel == "🆕 REGISTER NEW PRINTER"
    p_name = st.text_input("Model Name") if is_new else p_sel
    p_item = st.text_input("Part Name")
    p_qty = st.number_input("Qty", min_value=0, key="pq")
    p_prc = st.number_input("Cost (£)", min_value=0.0, key="pp")
    p_lnk = st.text_input("Reorder Link", key="plink")
    
    label = "🚀 Add Printer to Fleet" if is_new else "🔧 Save Part"
    if st.button(label):
        new_row = pd.DataFrame([["Printer Part", str(p_name), str(p_item), "---", p_qty, 1, p_prc, str(p_lnk), "N/A", str(date.today()), "---"]], columns=columns)
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=SQL_URL, data=df)
        st.cache_data.clear()
        st.rerun()

# --- 3. TABS: VIEW, ADJUST & DELETE ---
tabs = st.tabs(["🌈 STOCK"] + [f"🖥️ {p.upper()}" for p in p_list])

# Stock Tab
with tabs[0]:
    f_data = df[df["Category"] == "Filament"]
    st.dataframe(f_data[["Item", "Spec", "Quantity", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
    
    ca, cd = st.columns(2)
    with ca:
        with st.expander("🔢 Adjust Weight"):
            adj_f = st.selectbox("Select Spool", f_data['Item'] + " (" + f_data['Spec'] + ")", key="af")
            amt = st.number_input("Add/Sub (g)", value=0, key="famt")
            if st.button("Update"):
                df.loc[df["Item"] == adj_f.split(" (")[0], "Quantity"] += amt
                conn.update(spreadsheet=SQL_URL, data=df)
                st.cache_data.clear()
                st.rerun()
    with cd:
        with st.expander("🗑️ Delete Spool"):
            del_f = st.selectbox("Delete Spool", f_data['Item'] + " (" + f_data['Spec'] + ")", key="df")
            if st.button("❌ Remove"):
                df = df.drop(df[df["Item"] == del_f.split(" (")[0]].index)
                conn.update(spreadsheet=SQL_URL, data=df)
                st.cache_data.clear()
                st.rerun()

# Printer Tabs
for i, p in enumerate(p_list):
    with tabs[i+1]:
        p_data = df[(df["Printer"] == p) & (df["Category"] == "Printer Part")]
        st.dataframe(p_data[["Item", "Quantity", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
        
        # Similar Adjust/Delete Logic for Parts...
        with st.expander(f"🗑️ Delete {p} Part"):
            del_p = st.selectbox("Select Part", p_data['Item'], key=f"dp_{p}")
            if st.button(f"❌ Delete {del_p}", key=f"db_{p}"):
                df = df.drop(df[(df["Printer"] == p) & (df["Item"] == del_p)].index)
                conn.update(spreadsheet=SQL_URL, data=df)
                st.cache_data.clear()
                st.rerun()
