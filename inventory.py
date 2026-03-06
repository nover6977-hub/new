import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, date

# --- 1. UI SETUP & CONNECTION ---
st.set_page_config(page_title="PrintMaster Pro", layout="wide")

# High-Visibility CSS
st.markdown("""
    <style>
    * { color: black !important; font-weight: 700 !important; }
    .stApp { background-color: #FFFFFF !important; }
    h1, h3 { color: #D32F2F !important; }
    .stButton>button { background: #1976D2 !important; color: white !important; width: 100%; }
    .wishlist-card { background-color: #FFF3E0; border: 2px solid #FF9800; padding: 15px; border-radius: 10px; text-align: center; }
    .delete-btn button { background-color: #FF4B4B !important; }
    </style>
    """, unsafe_allow_html=True)

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="0s")

full_df = load_data()

# Data Cleaning
columns = ["Category", "Printer", "Item", "Spec", "Quantity", "Min_Stock", "Cost", "Buy_Link", "Last_Dried", "Last_Maintenance", "Location"]
full_df = full_df.reindex(columns=columns)
full_df[['Item', 'Spec', 'Printer', 'Location', 'Buy_Link']] = full_df[['Item', 'Spec', 'Printer', 'Location', 'Buy_Link']].astype(str)

# Split data
inventory_df = full_df[full_df["Category"] != "Wishlist"].copy()
wishlist_df = full_df[full_df["Category"] == "Wishlist"].copy()

st.title("🚀 PRINTMASTER PRO: COMMAND CENTER")

# --- 2. WISH LIST & BUDGET CALCULATOR ---
with st.expander("📝 SHOPPING WISH LIST & BUDGET"):
    w_col1, w_col2 = st.columns([2, 1])
    with w_col1:
        if not wishlist_df.empty:
            st.dataframe(wishlist_df[["Item", "Spec", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
            total_wish = pd.to_numeric(wishlist_df["Cost"]).sum()
        else:
            st.info("Wish list is empty.")
            total_wish = 0.0
    with w_col2:
        st.markdown(f'<div class="wishlist-card">💰 TOTAL BUDGET<br><h1>£{total_wish:.2f}</h1></div>', unsafe_allow_html=True)
        w_item = st.text_input("Item Name", key="wi")
        w_cost = st.number_input("Price (£)", min_value=0.0, key="wc")
        w_link = st.text_input("Link", key="wl")
        if st.button("✨ Add to Wish List"):
            new_w = pd.DataFrame([["Wishlist", "N/A", str(w_item), "---", 0, 0, w_cost, str(w_link), "N/A", "N/A", "N/A"]], columns=columns)
            updated_df = pd.concat([full_df, new_w], ignore_index=True)
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.rerun()
        if not wishlist_df.empty:
            if st.button("🗑️ Clear Wish List"):
                updated_df = full_df[full_df["Category"] != "Wishlist"]
                conn.update(data=updated_df)
                st.cache_data.clear()
                st.rerun()

st.divider()

# --- 3. G-CODE AUTO-DEDUCT ---
with st.expander("📂 G-CODE WEIGHT DEDUCTION"):
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        gfile = st.file_uploader("Upload .gcode", type=['gcode'])
        g_weight = 0.0
        if gfile:
            text = gfile.read().decode("utf-8", errors="ignore")
            match = re.search(r"filament used \[g\] = ([\d.]+)", text)
            if match: g_weight = float(match.group(1))
            if g_weight > 0: st.success(f"Deducting: {g_weight}g")
    with g_col2:
        fil_opts = (inventory_df[inventory_df["Category"]=="Filament"]['Item'] + " (" + inventory_df[inventory_df["Category"]=="Filament"]['Spec'] + ")").tolist()
        target_f = st.selectbox("Select Spool", fil_opts if fil_opts else ["No Filament"])
        if st.button("🔥 Confirm Deduction") and g_weight > 0:
            f_name = target_f.split(" (")[0]
            full_df.loc[full_df["Item"] == f_name, "Quantity"] = pd.to_numeric(full_df.loc[full_df["Item"] == f_name, "Quantity"]) - g_weight
            conn.update(data=full_df)
            st.cache_data.clear()
            st.rerun()

st.divider()

# --- 4. ADD TO INVENTORY ---
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🧶 Add Filament")
    fn, fs = st.text_input("Material", key="fn"), st.text_input("Color", key="fs")
    fq, fp = st.number_input("Weight (g)", key="fq"), st.number_input("Price (£)", key="fp")
    fl = st.text_input("Buy Link", key="fll")
    if st.button("➕ Add to Stock"):
        new_f = pd.DataFrame([["Filament", "Global", str(fn), str(fs), fq, 200, fp, str(fl), str(date.today()), "N/A", ""]], columns=columns)
        updated_df = pd.concat([full_df, new_f], ignore_index=True)
        conn.update(data=updated_df)
        st.cache_data.clear()
        st.rerun()

with c2:
    st.markdown("### 🛠️ Add Printer / Part")
    p_list = sorted(inventory_df[inventory_df["Printer"] != "Global"]["Printer"].unique().tolist())
    p_sel = st.selectbox("Assign to:", ["🆕 NEW PRINTER"] + p_list)
    is_new = p_sel == "🆕 NEW PRINTER"
    pn = st.text_input("Model Name") if is_new else p_sel
    pi = st.text_input("Part Name")
    pq, pc = st.number_input("Qty", key="pq"), st.number_input("Part Cost (£)", key="pc")
    pl = st.text_input("Link", key="pll")
    
    btn_label = "🚀 Add Printer to Fleet" if is_new else "🔧 Save Part"
    if st.button(btn_label):
        new_p = pd.DataFrame([["Printer Part", str(pn), str(pi), "---", pq, 1, pc, str(pl), "N/A", str(date.today()), ""]], columns=columns)
        updated_df = pd.concat([full_df, new_p], ignore_index=True)
        conn.update(data=updated_df)
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- 5. TABS & ADJUSTERS ---
tabs = st.tabs(["🌈 FILAMENT"] + [f"🖥️ {p.upper()}" for p in p_list])

with tabs[0]:
    f_data = inventory_df[inventory_df["Category"] == "Filament"]
    st.dataframe(f_data[["Item", "Spec", "Quantity", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
    
    adj_col, del_col = st.columns(2)
    with adj_col:
        with st.expander("🔢 Quick Adjust"):
            target = st.selectbox("Select Spool", f_data['Item'], key="adj_f")
            amt = st.number_input("Change (g)", value=0, key="f_amt")
            if st.button("Update Weight"):
                full_df.loc[full_df["Item"] == target, "Quantity"] = pd.to_numeric(full_df.loc[full_df["Item"] == target, "Quantity"]) + amt
                conn.update(data=full_df)
                st.cache_data.clear()
                st.rerun()
    with del_col:
        with st.expander("🗑️ Delete Spool"):
            target_del = st.selectbox("Delete Spool", f_data['Item'], key="del_f")
            if st.button("❌ Permanent Delete"):
                full_df = full_df.drop(full_df[full_df["Item"] == target_del].index)
                conn.update(data=full_df)
                st.cache_data.clear()
                st.rerun()

for i, p in enumerate(p_list):
    with tabs[i+1]:
        p_data = inventory_df[(inventory_df["Printer"] == p) & (inventory_df["Category"] == "Printer Part")]
        st.dataframe(p_data[["Item", "Quantity", "Cost", "Buy_Link"]], use_container_width=True, hide_index=True)
        # Delete Part Logic
        if st.button(f"🗑️ Wipe {p} Data", key=f"wipe_{p}"):
            full_df = full_df.drop(full_df[full_df["Printer"] == p].index)
            conn.update(data=full_df)
            st.cache_data.clear()
            st.rerun()
