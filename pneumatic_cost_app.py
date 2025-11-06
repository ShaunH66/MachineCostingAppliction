import streamlit as st
import pandas as pd
import math

# --- Page Configuration ---
st.set_page_config(
    page_title="Pneumatic Machine Cost Calculator",
    page_icon="💨",
    layout="wide"
)

# --- Initialize Session State for the Cylinder Data ---
# This is crucial to "remember" the user's table data between reruns.
if 'cylinder_df' not in st.session_state:
    st.session_state.cylinder_df = pd.DataFrame(
        [
            {"Quantity": 2, "Bore (mm)": 50.0, "Stroke (mm)": 200.0},
            {"Quantity": 4, "Bore (mm)": 25.0, "Stroke (mm)": 100.0},
        ]
    )

# --- Main Application ---
st.title("💨 Advanced Pneumatic Cost Calculator")
st.markdown("Created by Shaun Harris")
st.markdown("Calculate running costs for a machine with **multiple, different-sized** pneumatic cylinders.")
st.markdown("---")

# --- Sidebar for Global Inputs ---
# These parameters apply to the entire machine.
st.sidebar.header("⚙️ Global Machine & Cost Inputs")

# Machine Operation
st.sidebar.subheader("Machine Operation")
cycle_rate = st.sidebar.slider("Cycle Rate (cycles/minute)", min_value=1, max_value=120, value=20, help="How many full extend-and-retract cycles the entire machine performs per minute.")
pressure_bar = st.sidebar.slider("Operating Pressure (bar)", min_value=1.0, max_value=10.0, value=6.0, step=0.1)

# Operational Hours
st.sidebar.subheader("Operating Schedule")
hours_per_day = st.sidebar.slider("Hours per Day", 1, 24, 8)
days_per_week = st.sidebar.slider("Days per Week", 1, 7, 5)

# Cost and Efficiency
st.sidebar.subheader("Cost & Efficiency")
electricity_cost = st.sidebar.number_input("Cost of Electricity (£/kWh)", min_value=0.01, max_value=1.0, value=0.12, step=0.01)
compressor_efficiency = st.sidebar.slider(
    "Compressor Energy Rate (kWh/m³ of free air)", 
    min_value=0.05, 
    max_value=0.3, 
    value=0.15, 
    step=0.01,
    help="This represents how much energy your compressor uses to generate 1 cubic meter of standard air. A modern, efficient system is around 0.1-0.15 kWh/m³."
)

# --- Main Panel for Cylinder Definitions ---
st.header("🔧 Define Your Cylinders")
st.markdown("Use the table below to list all cylinder types on your machine. Double-click a cell to edit. Use the `+` button at the bottom to add a new type.")

# Use the data editor to get user input for the cylinders
edited_df = st.data_editor(
    st.session_state.cylinder_df,
    num_rows="dynamic",
    use_container_width=True
)
# Update the session state with the latest edits
st.session_state.cylinder_df = edited_df

# --- Calculation Logic ---

total_free_air_per_cycle_m3 = 0.0

# Iterate through each row (each cylinder type) in the DataFrame
for index, row in edited_df.iterrows():
    # Get values from the row, with defaults to prevent errors
    qty = row.get("Quantity", 0)
    bore_mm = row.get("Bore (mm)", 0.0)
    stroke_mm = row.get("Stroke (mm)", 0.0)

    # Proceed with calculation only if inputs are valid
    if qty > 0 and bore_mm > 0 and stroke_mm > 0:
        # 1. Convert inputs to standard units (meters)
        bore_m = bore_mm / 1000
        stroke_m = stroke_mm / 1000

        # 2. Calculate volume for a SINGLE cylinder of this type
        cylinder_area_m2 = math.pi * ((bore_m / 2) ** 2)
        cylinder_volume_m3 = cylinder_area_m2 * stroke_m

        # 3. Calculate air consumed per cycle for a SINGLE cylinder (double-acting)
        volume_per_cycle_m3 = 2 * cylinder_volume_m3

        # 4. Calculate Free Air consumption for a SINGLE cylinder
        free_air_per_cycle_m3_single = volume_per_cycle_m3 * (pressure_bar + 1)

        # 5. Add this group's consumption to the total for the whole machine
        total_free_air_per_cycle_m3 += free_air_per_cycle_m3_single * qty

# 6. Calculate total air consumption over time for the WHOLE machine
total_free_air_per_minute_m3 = total_free_air_per_cycle_m3 * cycle_rate
total_free_air_per_hour_m3 = total_free_air_per_minute_m3 * 60

# 7. Calculate energy consumption
kwh_per_hour = total_free_air_per_hour_m3 * compressor_efficiency

# 8. Calculate costs
cost_per_hour = kwh_per_hour * electricity_cost
cost_per_day = cost_per_hour * hours_per_day
cost_per_week = cost_per_day * days_per_week
cost_per_year = cost_per_week * 52 # Assuming 52 weeks in a year

# --- Display Results ---
st.markdown("---")
st.header("📊 Cost Analysis Results")

if edited_df.empty or edited_df["Quantity"].sum() == 0:
    st.warning("Please add at least one cylinder with a quantity greater than zero to the table above.")
else:
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Annual Cost", f"£{cost_per_year:,.2f}")
    col2.metric("🗓️ Weekly Cost", f"£{cost_per_week:,.2f}")
    col3.metric("⏱️ Hourly Cost", f"£{cost_per_hour:,.2f}")

    st.markdown("---")

    # Detailed Breakdown and Visualization
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Cost Breakdown")
        st.info(f"**Hourly:** £{cost_per_hour:,.2f}")
        st.info(f"**Daily:** £{cost_per_day:,.2f}")
        st.info(f"**Weekly:** £{cost_per_week:,.2f}")
        st.info(f"**Monthly (approx):** £{cost_per_year / 12:,.2f}")
        st.info(f"**Annual:** £{cost_per_year:,.2f}")

    with col2:
        st.subheader("Cost Over Time")
        chart_data = pd.DataFrame({
            "Period": ["Hourly", "Daily", "Weekly", "Monthly"],
            "Cost (£)": [cost_per_hour, cost_per_day, cost_per_week, cost_per_year / 12]
        })
        st.bar_chart(chart_data.set_index("Period"))

# --- Explanation Expander ---
with st.expander("📘 How is this calculated?"):
    st.markdown("""
    The cost is calculated by summing the air consumption of all the different cylinder types you define in the table.

    1.  **For Each Cylinder Type (each row in the table):**
        *   The volume of a single cylinder is calculated: `Volume = π * (Bore / 2)² * Stroke`.
        *   Air consumption per cycle is determined (assuming a **double-acting cylinder**, using air for both extend and retract strokes): `Air per Cycle = 2 * Volume`.
        *   This is converted to "Free Air" (air at atmospheric pressure) needed from the compressor: `Free Air = Compressed Air * (Pressure + 1)`.
        *   The total free air for that row is calculated: `Row Total Air = Free Air * Quantity`.

    2.  **Total Machine Consumption**:
        *   The air consumption from all rows is summed to get the total air needed for one full machine cycle.

    3.  **Consumption Over Time**:
        *   This total is multiplied by the machine's `Cycle Rate` to get the air demand per minute, which is then used to calculate hourly energy use (kWh).

    4.  **Final Cost**:
        *   The hourly energy use is multiplied by your `Electricity Cost` to determine the final cost, which is then extrapolated for daily, weekly, and annual periods.
    """)

# --- Footer ---
st.markdown("---")