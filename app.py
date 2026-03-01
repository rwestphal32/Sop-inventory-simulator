import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="S&OP Working Capital Simulator", layout="wide")

st.title("📦 10-SKU Portfolio S&OP Simulator")
st.caption("Manage Working Capital, Stockouts, and Pipeline Inventory across a complex product mix.")

# --- 1. DEFAULT SKU DATABASE ---
default_skus = [
    {"SKU": "Core Leather Lifting Belt", "Cost (£)": 18, "Price (£)": 60, "Weekly Demand": 800, "Volatility (%)": 10, "Lead Time (Wks)": 8, "Order Cost (£)": 500},
    {"SKU": "Pro Training Gloves", "Cost (£)": 8, "Price (£)": 25, "Weekly Demand": 1200, "Volatility (%)": 15, "Lead Time (Wks)": 6, "Order Cost (£)": 300},
    {"SKU": "Neoprene Knee Sleeves", "Cost (£)": 12, "Price (£)": 40, "Weekly Demand": 400, "Volatility (%)": 45, "Lead Time (Wks)": 3, "Order Cost (£)": 200},
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
    holding_cost_pct = st.slider("Annual Holding Cost (%)", 0.10, 0.40, 0.20, 0.02, help="Cost of capital, warehousing, and risk.")
    st.markdown("---")
    # Buttons still use use_container_width, but dataframes use width="stretch"
    run_sim = st.button("🔄 Run 52-Week Simulation", type="primary", use_container_width=True)

# --- MAIN UI TABS ---
tab1, tab2, tab3 = st.tabs(["🛠️ Portfolio Master Data", "📊 CFO Summary", "📥 52-Week Extract"])

with tab1:
    st.subheader("Edit SKU Parameters")
    st.write("Click into any cell to adjust unit economics, lead times, or demand volatility before running the simulation.")
    
    # Updated to width="stretch"
    edited_df = st.data_editor(
        st.session_state.sku_df, 
        width="stretch",
        hide_index=True,
        num_rows="dynamic"
    )
    st.session_state.sku_df = edited_df

if run_sim:
    with st.spinner("Running EOQ and Pipeline calculations across the portfolio..."):
        np.random.seed(42)
        weeks = 52
        sim_data = []
        summary_metrics = []

        for index, row in edited_df.iterrows():
            # Safe extraction in case of empty rows
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
            holding_cost_per_unit = cost * holding_cost_pct
            
            eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit) if holding_cost_per_unit > 0 else 0
            order_qty = int(eoq)
            
            std_dev_lt = np.std(demand) * np.sqrt(lt) if lt > 0 else 0
            safety_stock = int(1.64 * std_dev_lt) 
            reorder_point = int((mean_demand * lt) + safety_stock)
            
            on_hand = reorder_point + order_qty
            in_transit = [0] * (weeks + lt + 1)
            
            sku_rows = []
            stockouts = 0
            total_holding_cost = 0
            total_transit_capital = 0
            
            for w in range(weeks):
                arriving_today = in_transit[w]
                on_hand += arriving_today
                
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
                    "Week": w + 1,
                    "SKU": sku,
                    "Demand": current_demand,
                    "Sales": sales,
                    "End On-Hand": on_hand,
                    "Arriving Next": in_transit[w+1] if lt > 0 else 0,
                    "Capital in Warehouse (£)": inv_value,
                    "Capital on Ocean/Road (£)": transit_value
                })
            
            sim_data.extend(sku_rows)
            
            service_level = ((sum(demand) - stockouts) / sum(demand) * 100) if sum(demand) > 0 else 100.0
            avg_warehouse_cap = sum([r["Capital in Warehouse (£)"] for r in sku_rows]) / weeks
            avg_transit_cap = total_transit_capital / weeks
            
            summary_metrics.append({
                "SKU": sku,
                "Service Level (%)": service_level,
                "Lost Sales (£)": stockouts * price,
                "Avg. Capital in Warehouse (£)": avg_warehouse_cap,
                "Avg. Capital in Transit (£)": avg_transit_cap,
                "Total Cash Tied Up (£)": avg_warehouse_cap + avg_transit_cap,
                "Annual Holding Cost (£)": total_holding_cost
            })

        df_sim = pd.DataFrame(sim_data)
        df_summary = pd.DataFrame(summary_metrics)

        with tab2:
            st.subheader("Portfolio Financial Summary")
            
            total_cash = df_summary["Total Cash Tied Up (£)"].sum()
            total_lost = df_summary["Lost Sales (£)"].sum()
            avg_sl = df_summary["Service Level (%)"].mean()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Portfolio Cash Tied Up", f"£{total_cash:,.0f}")
            col2.metric("Total Lost Revenue (Stockouts)", f"£{total_lost:,.0f}")
            col3.metric("Average Portfolio Service Level", f"{avg_sl:.1f}%")
            
            st.markdown("---")
            st.write("**SKU-Level Financial Breakdown:**")
            
            # Apply gradient BEFORE format to avoid crash
            styled_df = (df_summary.style
                .background_gradient(subset=["Total Cash Tied Up (£)"], cmap="Reds")
                .background_gradient(subset=["Service Level (%)"], cmap="RdYlGn", vmin=85, vmax=100)
                .format({
                    "Service Level (%)": "{:.1f}%",
                    "Lost Sales (£)": "£{:,.0f}",
                    "Avg. Capital in Warehouse (£)": "£{:,.0f}",
                    "Avg. Capital in Transit (£)": "£{:,.0f}",
                    "Total Cash Tied Up (£)": "£{:,.0f}",
                    "Annual Holding Cost (£)": "£{:,.0f}"
                })
            )
            
            st.dataframe(styled_df, width="stretch", hide_index=True)

        with tab3:
            st.subheader("Raw Operations Data Extract")
            st.write("Export the 52-week item-level ledger to build pivot tables and diagnose specific stockout events.")
            csv = df_sim.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Full 52-Week Ledger (.CSV)",
                data=csv,
                file_name='Portfolio_Simulation_Ledger.csv',
                mime='text/csv',
            )
else:
    with tab2:
        st.info("👈 Edit your Master Data in Tab 1, then click 'Run 52-Week Simulation' in the sidebar.")
