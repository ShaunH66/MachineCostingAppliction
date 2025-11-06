import streamlit as st
import pandas as pd
import math

# --- Page Configuration ---
st.set_page_config(
    page_title="Machine Cost Calculator (Pneumatic & Servo)",
    page_icon="🤖",
    layout="wide"
)

# --- Initialize Session State for Component Data ---
if 'cylinder_df' not in st.session_state:
    st.session_state.cylinder_df = pd.DataFrame(
        [
            {"Quantity": 2, "Bore (mm)": 50.0, "Stroke (mm)": 200.0},
            {"Quantity": 4, "Bore (mm)": 25.0, "Stroke (mm)": 100.0},
        ]
    )
if 'servo_df' not in st.session_state:
    st.session_state.servo_df = pd.DataFrame(
        [
            {"Quantity": 1, "Motor Power (Watts)": 750, "Avg. Power Utilization (%)": 40},
            {"Quantity": 2, "Motor Power (Watts)": 200, "Avg. Power Utilization (%)": 60},
        ]
    )

# --- Main Application Title ---
st.title("🤖 Machine Running Cost Calculator")
st.markdown("Created by Shaun Harris")
st.markdown("Estimate the combined electricity cost for machines using both **pneumatic** and **servo** components.")
st.markdown("---")


# --- Sidebar for Global Inputs ---
st.sidebar.header("⚙️ Global Machine & Cost Inputs")

# Operational Hours
st.sidebar.subheader("Operating Schedule")
hours_per_day = st.sidebar.slider("Hours per Day", 1, 24, 8)
days_per_week = st.sidebar.slider("Days per Week", 1, 7, 5)

# Cost
st.sidebar.subheader("Electricity Cost")
electricity_cost = st.sidebar.number_input("Cost of Electricity (£/kWh)", min_value=0.01, max_value=1.0, value=0.12, step=0.01)


# --- Main Panel for Component Definitions using Tabs ---
tab1, tab2 = st.tabs(["💨 Pneumatic Components", "⚡ Servo Components"])

with tab1:
    st.header("Define Pneumatic Cylinders")
    
    col1, col2 = st.columns(2)
    with col1:
        cycle_rate = st.slider("Machine Cycle Rate (cycles/minute)", min_value=1, max_value=120, value=20)
        pressure_bar = st.slider("Operating Pressure (bar)", min_value=1.0, max_value=10.0, value=6.0, step=0.1)
    with col2:
        compressor_efficiency = st.slider(
            "Compressor Energy Rate (kWh/m³)", 
            min_value=0.05, 
            max_value=0.3, 
            value=0.15, 
            step=0.01,
            help="Energy to generate 1 m³ of free air. Modern systems are ~0.1-0.15 kWh/m³."
        )

    st.markdown("Use the table to list all cylinder types. Double-click to edit.")
    edited_cylinder_df = st.data_editor(
        st.session_state.cylinder_df,
        num_rows="dynamic",
        use_container_width=True
    )
    st.session_state.cylinder_df = edited_cylinder_df

with tab2:
    st.header("Define Servo Motors")
    st.markdown("List all servo motor types. `Avg. Power Utilization` is the estimated average load on the motor during a typical cycle, accounting for acceleration, holding, and idle time.")
    
    edited_servo_df = st.data_editor(
        st.session_state.servo_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Avg. Power Utilization (%)": st.column_config.NumberColumn(
                help="Enter a value from 0-100. This represents the average load on the motor over a full cycle."
            )
        }
    )
    st.session_state.servo_df = edited_servo_df

# --- Calculation Logic ---

# 1. PNEUMATIC CALCULATION
total_free_air_per_cycle_m3 = 0.0
for index, row in edited_cylinder_df.iterrows():
    qty, bore_mm, stroke_mm = row.get("Quantity", 0), row.get("Bore (mm)", 0.0), row.get("Stroke (mm)", 0.0)
    if qty > 0 and bore_mm > 0 and stroke_mm > 0:
        bore_m, stroke_m = bore_mm / 1000, stroke_mm / 1000
        cylinder_volume_m3 = math.pi * ((bore_m / 2) ** 2) * stroke_m
        volume_per_cycle_m3 = 2 * cylinder_volume_m3
        free_air_per_cycle_m3_single = volume_per_cycle_m3 * (pressure_bar + 1)
        total_free_air_per_cycle_m3 += free_air_per_cycle_m3_single * qty

total_free_air_per_hour_m3 = total_free_air_per_cycle_m3 * cycle_rate * 60
kwh_per_hour_pneumatic = total_free_air_per_hour_m3 * compressor_efficiency
cost_per_hour_pneumatic = kwh_per_hour_pneumatic * electricity_cost

# 2. SERVO CALCULATION
total_servo_power_watts = 0
for index, row in edited_servo_df.iterrows():
    qty, power_w, util_pct = row.get("Quantity", 0), row.get("Motor Power (Watts)", 0), row.get("Avg. Power Utilization (%)", 0)
    if qty > 0 and power_w > 0 and util_pct > 0:
        avg_power_per_motor_w = power_w * (util_pct / 100)
        total_servo_power_watts += avg_power_per_motor_w * qty

kwh_per_hour_servo = total_servo_power_watts / 1000 # Convert total watts to kWh
cost_per_hour_servo = kwh_per_hour_servo * electricity_cost

# 3. TOTAL CALCULATION
cost_per_hour_total = cost_per_hour_pneumatic + cost_per_hour_servo
cost_per_day_total = cost_per_hour_total * hours_per_day
cost_per_week_total = cost_per_day_total * days_per_week
cost_per_year_total = cost_per_week_total * 52

# --- Display Results ---
st.markdown("---")
st.header("📊 Total Cost Analysis")

if edited_cylinder_df.empty and edited_servo_df.empty:
    st.warning("Please add components in the tabs above to calculate costs.")
else:
    # Key Metrics for the ENTIRE machine
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Annual Cost", f"£{cost_per_year_total:,.2f}")
    col2.metric("🗓️ Total Weekly Cost", f"£{cost_per_week_total:,.2f}")
    col3.metric("⏱️ Total Hourly Cost", f"£{cost_per_hour_total:,.2f}")

    st.markdown("---")

    # Detailed Breakdown and Visualization
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Cost Contribution")
        
        # Data for the pie chart
        cost_data = {
            'System': ['Pneumatics', 'Servos'],
            'Hourly Cost (£)': [cost_per_hour_pneumatic, cost_per_hour_servo]
        }
        source = pd.DataFrame(cost_data)
        
        # Simple Pie Chart using st.altair_chart
        import altair as alt
        chart = alt.Chart(source).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Hourly Cost (£)", type="quantitative"),
            color=alt.Color(field="System", type="nominal", scale=alt.Scale(scheme='category10')),
            tooltip=['System', 'Hourly Cost (£)']
        ).properties(
            title='Cost Distribution'
        )
        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.subheader("Detailed Cost Breakdown")
        
        # Create a clean table for the breakdown
        breakdown_data = {
            "Period": ["Hourly", "Daily", "Weekly", "Annual"],
            "Pneumatics (£)": [
                cost_per_hour_pneumatic, 
                cost_per_hour_pneumatic * hours_per_day,
                cost_per_hour_pneumatic * hours_per_day * days_per_week,
                cost_per_hour_pneumatic * hours_per_day * days_per_week * 52
            ],
            "Servos (£)": [
                cost_per_hour_servo,
                cost_per_hour_servo * hours_per_day,
                cost_per_hour_servo * hours_per_day * days_per_week,
                cost_per_hour_servo * hours_per_day * days_per_week * 52
            ],
            "Total (£)": [
                cost_per_hour_total,
                cost_per_day_total,
                cost_per_week_total,
                cost_per_year_total
            ]
        }
        breakdown_df = pd.DataFrame(breakdown_data).set_index("Period")
        st.dataframe(breakdown_df.style.format("£{:,.2f}"))

# --- Explanation Expander ---
with st.expander("📘 How is this calculated?"):
    st.markdown("""
    The total cost is the sum of the costs from the pneumatic and servo systems, which are calculated independently.

    #### 💨 Pneumatic System Cost:
    1.  **Air Consumption per Cycle**: For each cylinder type, we calculate the free air required for one extend-and-retract cycle.
    2.  **Total Air Demand**: We sum the air consumption for all cylinders and multiply by the `Machine Cycle Rate` to get the total volume of air needed per minute (and then per hour).
    3.  **Energy Use**: This air volume is multiplied by the `Compressor Energy Rate` (its efficiency) to find the electricity consumed in kWh.
    4.  **Cost**: The result is multiplied by your `Electricity Cost`.

    #### ⚡ Servo System Cost:
    1.  **Average Power per Motor**: The `Motor Power (Watts)` is multiplied by the `Avg. Power Utilization (%)`. This estimates the real-world power draw, as servos are rarely at 100% load.
    2.  **Total Power Demand**: We sum the average power for all servo motors defined in the table.
    3.  **Energy Use**: The total power in Watts is converted to kilowatts (kW). Since this is an hourly rate, this value is equivalent to the kilowatt-hours (kWh) consumed in one hour.
    4.  **Cost**: This kWh value is multiplied by your `Electricity Cost`.
    """)

# --- Footer ---
st.markdown("---")
