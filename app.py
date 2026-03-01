import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats

st.set_page_config(page_title="S&OP Working Capital Simulator", layout="wide")

st.title("📦 10-SKU Portfolio S&OP Simulator")
st.caption("Newsvendor-Optimized Inventory Management & CPFR Retail Tracking")

# --- 1. DEFAULT SKU DATABASE ---
default_skus = [
    {"SKU": "Core Leather Lifting Belt", "Cost (£)": 18, "Price (£)": 60, "Weekly Demand": 800, "Volatility (%)": 10, "Lead Time (Wks)": 8, "Order Cost (£)": 500},
    {"SKU": "Pro Training Gloves", "Cost (£)": 8, "Price (£)": 25, "Weekly Demand": 1200, "Volatility (%)": 15, "Lead Time (Wks)": 6, "Order Cost (£)": 300},
    {"SKU": "Padded Cotton Lifting Strap", "Cost (£)": 4, "Price (£)": 15, "Weekly Demand": 3000, "Volatility (%)": 45, "Lead Time (Wks)": 10, "Order Cost (£)": 200},
    {"SKU": "Basic Speed Jump Rope", "Cost (£)": 3, "Price (£)": 15, "Weekly Demand": 2000, "Volatility (%)": 5, "Lead Time (Wks)": 8, "Order Cost (£)": 400},
    {"SKU": "Premium Yoga Mat", "Cost (£)": 15, "Price (£)": 65, "Weekly Demand": 500, "Volatility (%)": 60, "Lead Time (Wks)": 6, "Order Cost (£)": 350},
    {"SKU": "Resistance Band Set", "Cost (£)": 6, "Price (£)": 30, "Weekly Demand": 1500, "Volatility (%)": 20, "Lead Time (Wks)": 6, "Order Cost (£)": 300},
    {"SKU": "Chalk Block 8-Pack", "Cost (£)": 4, "Price (£)": 18, "Weekly Demand": 600, "Volatility (%)": 10, "Lead Time (Wks)": 2, "Order Cost (£)": 100},
    {"SKU": "High-Density Foam Roller", "Cost (£)": 9, "Price (£)": 35, "Weekly Demand": 450, "Volatility (%)": 25, "Lead Time (Wks)": 4, "Order Cost (£)": 250},
    {"SKU": "Tactical Weighted Vest", "Cost (£)": 45, "Price (£)": 130, "Weekly Demand": 150, "Volatility (%)": 50, "Lead Time (Wks)": 10, "Order Cost (£)": 600},
    {"SKU": "Cotton Wrist Wraps", "Cost (£)": 2, "Price (£)": 12, "Weekly Demand": 1800, "Volatility (%)": 30, "Lead Time (Wks)": 2, "Order Cost (£)": 100}
]

if 'sku_df' not in st.session_state:
    st.session_state.sku_df = pd.DataFrame(default_skus)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Financial Parameters")
    holding_cost_pct = st.slider("Annual Holding Cost (%)", 0.10, 0.40, 0.20, 0.02)
    st.markdown("---")
    run_sim = st.button("🔄 Run 52-Week Simulation", type="primary", use_container_width=True)

# --- MAIN UI TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🛠️ Portfolio Master Data", "📊 CFO Summary", "📥 52-Week Extract", "🏢 Retailer CPFR Simulator"])

with tab1:
    st.subheader("Edit SKU Parameters")
    edited_df = st.data_editor(st.session_state.sku_df, width="stretch", hide_index=True, num_rows="dynamic")
    st.session_state.sku_df = edited_df

if run_sim:
    with st.spinner("Applying Newsvendor Logic and Simulating Pipeline..."):
        np.random.seed(42)
        weeks = 52
        sim_data = []
        summary_metrics = []

        for index, row in edited_df.iterrows():
            sku = str(row.get("SKU", f"Item_{index}"))
            cost = float(row.get("Cost (£)", 0))
            price = float(row.get("Price (£)", 0))
            mean_demand = float(row.get("Weekly Demand", 0))
            vol = float(row.get("Volatility (%)", 0)) / 100.0
            lt = int(row.get("Lead Time (Wks)", 0))
            order_cost = float(row.get("Order Cost (£)", 0))
            
            demand = np.random.normal(mean_demand, mean_demand * vol, weeks) if mean_demand > 0 else np.zeros(weeks)
            demand = np.maximum(demand, 0).astype(int)
            annual_demand = sum(demand)
            
            margin = price - cost
            holding_cost_per_unit = cost * holding_cost_pct
            critical_ratio = margin / (margin + holding_cost_per_unit) if (margin + holding_cost_per_unit) > 0 else 0.90
            z_score = stats.norm.ppf(critical_ratio)
            
            eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit) if holding_cost_per_unit > 0 else 0
            order_qty = int(eoq)
            
            std_dev_lt = np.std(demand) * np.sqrt(lt) if lt > 0 else 0
            safety_stock = int(z_score * std_dev_lt) 
            reorder_point = int((mean_demand * lt) + safety_stock)
            
            on_hand = reorder_point + int(order_qty / 2)
            in_transit = [0] * (weeks + lt + 1)
            
            sku_rows = []
            stockouts = 0
            total_holding_cost, total_transit_capital = 0, 0
            
            for w in range(weeks):
                on_hand += in_transit[w]
                current_demand = demand[w]
                
                if on_hand >= current_demand:
                    sales = current_demand
                    on_hand -= current_demand
                else:
                    sales = on_hand
                    stockouts += (current_demand - on_hand)
                    on_hand = 0
                
                pipeline_inventory = sum(in_transit[w:w+lt]) if lt > 0 else 0
                if (on_hand + pipeline_inventory) <= reorder_point:
                    in_transit[w + lt] += order_qty
                
                inv_value = on_hand * cost
                transit_value = sum(in_transit[w:w+lt]) * cost if lt > 0 else 0
                weekly_holding = inv_value * (holding_cost_pct / 52)
                
                total_holding_cost += weekly_holding
                total_transit_capital += transit_value
                
                sku_rows.append({
                    "Week": w + 1, "SKU": sku, "Demand": current_demand, "Sales": sales,
                    "End On-Hand": on_hand, "Arriving Next": in_transit[w+1] if lt > 0 else 0,
                    "Capital in Warehouse (£)": inv_value, "Capital on Ocean/Road (£)": transit_value
                })
            
            sim_data.extend(sku_rows)
            actual_service_level = ((sum(demand) - stockouts) / sum(demand) * 100) if sum(demand) > 0 else 100.0
            summary_metrics.append({
                "SKU": sku, "Target SL (%)": critical_ratio * 100, "Actual SL (%)": actual_service_level,
                "Lost Sales (£)": stockouts * price,
                "Avg. Capital in Warehouse (£)": sum([r["Capital in Warehouse (£)"] for r in sku_rows]) / weeks,
                "Avg. Capital in Transit (£)": total_transit_capital / weeks,
                "Total Cash Tied Up (£)": (sum([r["Capital in Warehouse (£)"] for r in sku_rows]) / weeks) + (total_transit_capital / weeks)
            })

        df_sim = pd.DataFrame(sim_data)
        df_summary = pd.DataFrame(summary_metrics)

        # --- CPFR GHOST LEDGER SIMULATION ---
        # Simulating the DSG Padded Cotton Strap scenario
        cpfr_weeks = 20
        pos_baseline = 3000
        retailer_system_inv = 18000 # Retailer thinks they have 6 weeks of supply
        actual_physical_inv = 18000
        ghost_ledger_inv = 18000
        
        cpfr_data = []
        panic_triggered = False
        
        for w in range(1, cpfr_weeks + 1):
            # 1. Retailer POS Scans (EDI 852 data we receive)
            weekly_pos = int(np.random.normal(pos_baseline, pos_baseline * 0.15))
            
            # 2. Phantom Inventory occurs (Theft, backroom loss, mis-scans - approx 4% invisible shrink)
            phantom_shrink = int(weekly_pos * 0.04)
            
            # 3. The Retailer's blind reality vs Actual physical reality
            retailer_system_inv -= weekly_pos # Retailer ERP only deducts register scans
            actual_physical_inv -= (weekly_pos + phantom_shrink) # Reality deducts scans AND shrink
            
            # 4. Our "Ghost Ledger" (We mathematically assume a 5% shrink buffer just to be safe)
            ghost_ledger_inv -= int(weekly_pos * 1.05)
            
            # 5. Weeks of Supply (WOS) calculation
            retailer_wos = retailer_system_inv / pos_baseline
            ghost_wos = ghost_ledger_inv / pos_baseline
            
            status = "🟢 Stable"
            if ghost_wos <= 1.5:
                status = "🟡 Pre-Build Warning"
            
            # The exact moment the DSG shelves empty, but their computer says they have inventory
            if actual_physical_inv <= 0 and not panic_triggered:
                status = "🔴 PANIC PO INBOUND (Physical Stockout)"
                panic_triggered = True
                actual_physical_inv = 0 # Can't go below zero physically
                
            cpfr_data.append({
                "Week": w,
                "EDI POS Scans": weekly_pos,
                "Retailer ERP Inventory": max(retailer_system_inv, 0),
                "Retailer ERP WOS": round(retailer_wos, 1),
                "Our Ghost Ledger": max(ghost_ledger_inv, 0),
                "Our Ghost WOS": round(ghost_wos, 1),
                "Actionable Alert": status
            })
            
        df_cpfr = pd.DataFrame(cpfr_data)

        # UI RENDER LOGIC
        with tab2:
            st.subheader("CFO Portfolio Financial Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Portfolio Cash Tied Up", f"£{df_summary['Total Cash Tied Up (£)'].sum():,.0f}")
            col2.metric("Total Lost Revenue (Stockouts)", f"£{df_summary['Lost Sales (£)'].sum():,.0f}")
            col3.metric("Average Portfolio Service Level", f"{df_summary['Actual SL (%)'].mean():,.1f}%")
            st.dataframe(df_summary.style.format({"Target SL (%)": "{:.1f}%", "Actual SL (%)": "{:.1f}%", "Lost Sales (£)": "£{:,.0f}", "Avg. Capital in Warehouse (£)": "£{:,.0f}", "Avg. Capital in Transit (£)": "£{:,.0f}", "Total Cash Tied Up (£)": "£{:,.0f}"}), width="stretch", hide_index=True)

        with tab3:
            st.subheader("Raw Operations Data Extract")
            st.download_button(label="📥 Download Full 52-Week Ledger (.CSV)", data=df_sim.to_csv(index=False).encode('utf-8'), file_name='Newsvendor_Simulation_Ledger.csv', mime='text/csv')

        with tab4:
            st.subheader("Retailer CPFR 'Ghost Ledger' Tracker")
            st.write("Simulating a major big-box retailer (e.g., Dick's Sporting Goods) for the **Padded Cotton Lifting Strap**.")
            st.markdown("""
            * **The Trap:** The retailer's ERP system only tracks register scans, completely ignoring 'Phantom Inventory' (theft, backroom loss). 
            * **The Strategy:** We calculate a 'Ghost Ledger' to buffer for invisible shrink. Notice how our system triggers a **Pre-Build Warning** weeks before the retailer's physical shelves actually hit zero, allowing us to prep raw materials before their panic order drops.
            """)
            
            def highlight_alerts(val):
                if "PANIC" in str(val): return 'background-color: #ffcccc; color: #900000; font-weight: bold'
                elif "Warning" in str(val): return 'background-color: #fff4cc; color: #806000'
                return ''
                
            st.dataframe(df_cpfr.style.map(highlight_alerts, subset=['Actionable Alert']), width="stretch", hide_index=True)
else:
    with tab2:
        st.info("👈 Edit your Master Data in Tab 1, then click 'Run 52-Week Simulation' in the sidebar.")
