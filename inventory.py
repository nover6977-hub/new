import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date

# --- DATABASE SETUP ---
DATA_FILE = "inventory_v4.csv"
columns = ["Category", "Printer", "Item", "Spec", "Quantity", "Min_Stock", "Cost", "Buy_Link", "Last_Dried", "Last_Maintenance", "Location"]

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for col in columns:
        if col not in df.columns:
            df[col] = 0.0 if col == "Cost" else "---"
    df[['Item', 'Spec', 'Printer', 'Location', 'Buy_Link']] = df[['Item', 'Spec', 'Printer', 'Location', 'Buy_Link']].astype(str)
else:
    df = pd.DataFrame(columns=columns)

# --- G-CODE PARSER ---
def parse_gcode(file_bytes):
    text = file_bytes.decode("utf-8", errors="ignore")
    patterns = [r"filament used \[g\] = ([\d.]+)", r"total filament used \[g\]: ([\d.]+)", r"filament used: ([\d.]+)g"]
    for p in patterns:
        match = re.search(p, text)
        if match: return float(match.group(1))
    return 0.0

# --- UI STYLING (Forced Visibility & High Contrast) ---
st.set_page_config(page_title="PrintMaster Pro", layout="wide")
st.markdown("""
    <style>
    * { color: black !important; font-weight: 700 !important; }
    .stApp { background-color: #FFFFFF !important; }
    h1, h3 { color: #D32F2F !important; }
    .stButton>button { background: #1976D2 !important; color: white !important; width: 100%; }
    .delete-section { border: 2px solid #FF4B4B; padding: 10px; border-radius: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 PRINTMASTER PRO: ALL-IN-ONE")

# --- 1. G-CODE ANALYZER ---
with st.expander("📂 G-CODE AUTO-DEDUCT ENGINE", expanded=False):
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        gfile = st.file_uploader("Upload .gcode", type=['gcode'])
        g_weight = parse_gcode(gfile.read()) if gfile else 0.0
        if g_weight > 0: st.success(f"G-Code Weight: {g_weight}g")
    with g_col2:
        fil_opts = (df[df["Category"]=="Filament"]['Item'] + " (" + df[df["Category"]=="Filament"]['Spec'] + ")").tolist()
        target_f = st.selectbox("Select Spool to Deduct From", fil_opts if fil_opts else ["No Filament Found"])
        if st.button("🔥 Confirm & Deduct Weight") and g_weight > 0:
            f_name = target_f.split(" (")[0]
            df.loc[df["Item"] == f_name, "Quantity"] -= g_weight
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

st.divider()

# --- 2. ADD SECTIONS ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    st.markdown("### 🧶 Add Filament")
    f_n = st.text_input("Material (e.g. PLA)", key="fn")
    f_s = st.text_input("Brand/Color", key="fs")
    ca, cb = st.columns(2)
    with ca: f_q = st.number_input("Starting Weight (g)", min_value=0, key="fq")
    with cb: f_p = st.number_input("Price (£)", min_value=0.0, key="fp")
    f_link = st.text_input("Purchase Link (URL)", key="flink")
    if st.button("➕ Add Filament Spool"):
        new_f = pd.DataFrame([["Filament", "Global", str(f_n), str(f_s), f_q, 200, f_p, str(f_link), str(date.today()), "N/A", ""]], columns=columns)
        df = pd.concat([df, new_f], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

with col_in2:
    st.markdown("### 🛠️ Add Printer or Part")
    p_list_exists = sorted(df[df["Printer"] != "Global"]["Printer"].unique().tolist())
    p_sel = st.selectbox("Where does this go?", ["🆕 REGISTER NEW PRINTER"] + p_list_exists)
    is_new = p_sel == "🆕 REGISTER NEW PRINTER"
    p_name = st.text_input("Model Name (e.g. Ender 5 Max)") if is_new else p_sel
    p_item = st.text_input("Part/Item Name")
    cc, cd = st.columns(2)
    with cc: p_q = st.number_input("Qty", min_value=0, key="pq")
    with cd: p_p = st.number_input("Cost (£)", min_value=0.0, key="pp")
    p_link = st.text_input("Buy Link", key="plink")
    
    # Smart Label Logic
    label = "🚀 Add Printer to Fleet" if is_new else "🔧 Save Part to Inventory"
    if st.button(label):
        new_p = pd.DataFrame([["Printer Part", str(p_name), str(p_item), "---", p_q, 1, p_p, str(p_link), "N/A", str(date.today()), "---"]], columns=columns)
        df = pd.concat([df, new_p], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

st.divider()

# --- 3. TABS: VIEW, ADJUST & DELETE ---
tabs = st.tabs(["🌈 FILAMENT HUB"] + [f"🖥️ {p.upper()}" for p in p_list_exists])

# --- FILAMENT HUB ---
with tabs[0]:
    f_data = df[df["Category"] == "Filament"]
    st.dataframe(f_data[["Item", "Spec", "Quantity", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
    
    c_adj, c_del = st.columns(2)
    with c_adj:
        with st.expander("🔢 Quick Weight Tweak"):
            adj_f = st.selectbox("Select Spool", f_data['Item'] + " (" + f_data['Spec'] + ")", key="adj_f")
            amt = st.number_input("Add/Subtract (g)", value=0, key="f_amt")
            if st.button("Update Weight"):
                n = adj_f.split(" (")[0]
                df.loc[df["Item"] == n, "Quantity"] += amt
                df.to_csv(DATA_FILE, index=False)
                st.rerun()
    with c_del:
        with st.expander("🗑️ PERMANENT REMOVAL"):
            del_f = st.selectbox("Select Spool to Delete", f_data['Item'] + " (" + f_data['Spec'] + ")", key="del_f")
            if st.button("❌ DELETE FROM DATABASE"):
                n = del_f.split(" (")[0]
                df = df.drop(df[df["Item"] == n].index)
                df.to_csv(DATA_FILE, index=False)
                st.rerun()

# --- PRINTER TABS ---
for i, p in enumerate(p_list_exists):
    with tabs[i+1]:
        p_data = df[(df["Printer"] == p) & (df["Category"] == "Printer Part")]
        st.dataframe(p_data[["Item", "Quantity", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
        
        pa_col, pd_col = st.columns(2)
        with pa_col:
            with st.expander(f"🔢 Adjust {p} Stock"):
                adj_p = st.selectbox("Select Part", p_data['Item'], key=f"adj_{p}")
                p_amt = st.number_input("Change Qty (+/-)", value=0, key=f"v_{p}")
                if st.button("Update Stock", key=f"b_{p}"):
                    df.loc[(df["Printer"] == p) & (df["Item"] == adj_p), "Quantity"] += p_amt
                    df.to_csv(DATA_FILE, index=False)
                    st.rerun()
        with pd_col:
            with st.expander(f"🗑️ Delete {p} Part"):
                del_p = st.selectbox("Select Part to Wipe", p_data['Item'], key=f"dp_{p}")
                if st.button(f"❌ DELETE {del_p}", key=f"db_{p}"):
                    df = df.drop(df[(df["Printer"] == p) & (df["Item"] == del_p)].index)
                    df.to_csv(DATA_FILE, index=False)
                    st.rerun()