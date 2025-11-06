import streamlit as st
import pandas as pd
import math
import altair as alt

# --- Page Configuration ---
st.set_page_config(
    page_title="Machine Cost Calculator",
    page_icon="🤖",
    layout="wide"
)

# --- Initialize Session State for Component Data ---
if 'cylinder_df' not in st.session_state:
    st.session_state.cylinder_df = pd.DataFrame(
        [
            {"Quantity": 2, "Bore (mm)": 160.0, "Stroke (mm)": 600.0},
            {"Quantity": 2, "Bore (mm)": 50.0, "Stroke (mm)": 200.0}
        ]
    )
if 'servo_df' not in st.session_state:
    st.session_state.servo_df = pd.DataFrame(
        [
            {"Quantity": 1, "Motor Power (Watts)": 1750, "Avg. Power Utilization (%)": 25},
            {"Quantity": 1, "Motor Power (Watts)": 1200, "Avg. Power Utilization (%)": 25}
        ]
    )

# --- Main Application Title ---
st.title("🤖 Advanced Machine Running Cost Calculator")
st.markdown("Created By Shaun Harris")
st.markdown("Estimate costs for machines with **pneumatics (including safety dumps)** and **servos**.")
st.markdown("---")

# --- Sidebar for Global Inputs ---
st.sidebar.header("⚙️ Global Machine & Cost Inputs")
st.sidebar.subheader("Operating Schedule")
hours_per_day = st.sidebar.slider("Hours per Day", 1, 24, 8)
days_per_week = st.sidebar.slider("Days per Week", 1, 7, 5)

st.sidebar.subheader("Financial Inputs")
currency = st.sidebar.selectbox("Select Currency", ["£", "$", "€"])
electricity_cost = st.sidebar.number_input(f"Cost of Electricity ({currency}/kWh)", 0.01, 1.0, 0.12, 0.01)

# --- Main Panel for Component Definitions using Tabs ---
tab1, tab2 = st.tabs(["💨 Pneumatic Components", "⚡ Servo Components"])

with tab1:
    st.header("Define Pneumatic System")
    st.subheader("1. Actuation Parameters")
    col1, col2 = st.columns(2)
    with col1:
        cycle_rate = st.slider("Machine Cycle Rate (cycles/minute)", 1, 120, 5)
        pressure_bar = st.slider("Operating Pressure (bar)", 1.0, 10.0, 6.0, 0.1)
    with col2:
        compressor_efficiency = st.slider("Compressor Energy Rate (kWh/m³)", 0.05, 0.3, 0.15, 0.01, help="Energy to generate 1 m³ of free air.")
    st.markdown("List all cylinder types used for machine actuation.")
    edited_cylinder_df = st.data_editor(st.session_state.cylinder_df, num_rows="dynamic", use_container_width=True, column_config={"Quantity": st.column_config.NumberColumn(required=True), "Bore (mm)": st.column_config.NumberColumn(required=True), "Stroke (mm)": st.column_config.NumberColumn(required=True)})
    st.session_state.cylinder_df = edited_cylinder_df
    st.markdown("---")
    st.subheader("2. Safety System Air Dump (Waste)")
    dump_air = st.toggle("Machine dumps system air on safety event", value=True)
    if dump_air:
        receiver_liters = st.number_input("Local Air Receiver Volume (Liters)", 0, 1000, 10, help="Look for a data plate on the machine's air tank.")
        dump_trigger_method = st.radio("How is the air dump triggered?", ("Based on random safety events per hour", "After every machine cycle"), horizontal=True, label_visibility="collapsed")
        if dump_trigger_method == "Based on random safety events per hour":
            dumps_per_hour = st.number_input("Safety Dump Events per Hour", 0, 120, 4, help="How many times per hour is the safety system triggered?")
        else:
            dumps_per_hour = 0

with tab2:
    st.header("Define Servo Motors")
    st.markdown("List all servo motors. `Avg. Power Utilization` is the estimated average load during a cycle.")
    edited_servo_df = st.data_editor(st.session_state.servo_df, num_rows="dynamic", use_container_width=True, column_config={"Quantity": st.column_config.NumberColumn(required=True), "Motor Power (Watts)": st.column_config.NumberColumn(required=True), "Avg. Power Utilization (%)": st.column_config.NumberColumn(min_value=0, max_value=100, required=True)})
    st.session_state.servo_df = edited_servo_df

# --- Calculation Logic ---

# 1. PNEUMATIC ACTUATION CALCULATION
total_free_air_per_cycle_m3 = 0.0
# --- FIX: Use .to_dict('records') for safe iteration ---
for row in edited_cylinder_df.to_dict('records'):
    qty, bore_mm, stroke_mm = row.get("Quantity", 0), row.get("Bore (mm)", 0.0), row.get("Stroke (mm)", 0.0)
    if qty > 0 and bore_mm > 0 and stroke_mm > 0:
        bore_m, stroke_m = bore_mm/1000, stroke_mm/1000
        cylinder_volume_m3 = math.pi * ((bore_m/2)**2) * stroke_m
        free_air_per_cycle = (2 * cylinder_volume_m3) * (pressure_bar + 1)
        total_free_air_per_cycle_m3 += free_air_per_cycle * qty

total_actuation_air_per_hour_m3 = total_free_air_per_cycle_m3 * cycle_rate * 60
kwh_per_hour_pneumatic_actuation = total_actuation_air_per_hour_m3 * compressor_efficiency
cost_per_hour_pneumatic_actuation = kwh_per_hour_pneumatic_actuation * electricity_cost

# 2. PNEUMATIC WASTE (SAFETY DUMP) CALCULATION
cost_per_hour_pneumatic_waste = 0
if dump_air and receiver_liters > 0:
    receiver_m3 = receiver_liters / 1000
    free_air_per_dump_m3 = receiver_m3 * (pressure_bar + 1)
    if dump_trigger_method == "Based on random safety events per hour":
        total_waste_air_per_hour_m3 = free_air_per_dump_m3 * dumps_per_hour
    else:
        dumps_per_hour_from_cycles = cycle_rate * 60
        total_waste_air_per_hour_m3 = free_air_per_dump_m3 * dumps_per_hour_from_cycles
    kwh_per_hour_pneumatic_waste = total_waste_air_per_hour_m3 * compressor_efficiency
    cost_per_hour_pneumatic_waste = kwh_per_hour_pneumatic_waste * electricity_cost

# 3. SERVO CALCULATION
total_servo_power_watts = 0
# --- FIX: Use .to_dict('records') for safe iteration ---
for row in edited_servo_df.to_dict('records'):
    qty, power_w, util_pct = row.get("Quantity", 0), row.get("Motor Power (Watts)", 0), row.get("Avg. Power Utilization (%)", 0)
    if qty > 0 and power_w > 0 and util_pct >= 0:
        avg_power_per_motor_w = power_w * (util_pct / 100)
        total_servo_power_watts += avg_power_per_motor_w * qty

kwh_per_hour_servo = total_servo_power_watts / 1000
cost_per_hour_servo = kwh_per_hour_servo * electricity_cost

# 4. TOTAL CALCULATION
cost_per_hour_total = cost_per_hour_pneumatic_actuation + cost_per_hour_pneumatic_waste + cost_per_hour_servo
cost_per_day_total = cost_per_hour_total * hours_per_day
cost_per_week_total = cost_per_day_total * days_per_week
cost_per_year_total = cost_per_week_total * 52

# --- Display Results ---
st.markdown("---")
st.header("📊 Total Cost Analysis")

if not any([cost_per_hour_pneumatic_actuation, cost_per_hour_pneumatic_waste, cost_per_hour_servo]):
    st.warning("Please add components in the tabs above to calculate costs.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Annual Cost", f"{currency}{cost_per_year_total:,.2f}")
    col2.metric("🗓️ Total Weekly Cost", f"{currency}{cost_per_week_total:,.2f}")
    col3.metric("⏱️ Total Hourly Cost", f"{currency}{cost_per_hour_total:,.2f}")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Cost Contribution")
        hourly_cost_col_name = f'Hourly Cost ({currency})'
        cost_data = {
            'System': ['Pneumatic Actuation', 'Pneumatic Waste', 'Servos'],
            hourly_cost_col_name: [cost_per_hour_pneumatic_actuation, cost_per_hour_pneumatic_waste, cost_per_hour_servo]
        }
        source = pd.DataFrame(cost_data)
        source = source[source[hourly_cost_col_name] > 0]
        
        if not source.empty:
            chart = alt.Chart(source).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field=hourly_cost_col_name, type="quantitative"),
                color=alt.Color(field="System", type="nominal", scale=alt.Scale(scheme='set1'), title="Cost Source"),
                tooltip=['System', alt.Tooltip(hourly_cost_col_name, format=',.2f')]
            ).properties(title='Cost Distribution per Hour')
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No costs to display. Please check your inputs.")
            
    with col2:
        st.subheader("Detailed Cost Breakdown")
        breakdown_data = {
            f"Pneumatic Actuation ({currency})": [cost_per_hour_pneumatic_actuation, cost_per_hour_pneumatic_actuation * hours_per_day, cost_per_hour_pneumatic_actuation * hours_per_day * days_per_week, cost_per_hour_pneumatic_actuation * hours_per_day * days_per_week * 52],
            f"Pneumatic Waste ({currency})": [cost_per_hour_pneumatic_waste, cost_per_hour_pneumatic_waste * hours_per_day, cost_per_hour_pneumatic_waste * hours_per_day * days_per_week, cost_per_hour_pneumatic_waste * hours_per_day * days_per_week * 52],
            f"Servos ({currency})": [cost_per_hour_servo, cost_per_hour_servo * hours_per_day, cost_per_hour_servo * hours_per_day * days_per_week, cost_per_hour_servo * hours_per_day * days_per_week * 52],
            f"Total ({currency})": [cost_per_hour_total, cost_per_day_total, cost_per_week_total, cost_per_year_total]
        }
        breakdown_df = pd.DataFrame(breakdown_data, index=["Hourly", "Daily", "Weekly", "Annual"])
        st.dataframe(breakdown_df.style.format(f"{currency}{{:.2f}}"))

# --- Explanation Expander ---
with st.expander("📘 How is this calculated?"):
    st.markdown("""
    The total cost is the sum of three independently calculated components:

    #### 1. 💨 Pneumatic Actuation Cost
    This is the cost of the air used to **move the cylinders**.
    - It's calculated based on cylinder dimensions, quantity, and the `Machine Cycle Rate`.

    #### 2. 🗑️ Pneumatic Waste (Safety Dump) Cost
    This is the cost of air lost when the system is purged. The calculation depends on the trigger you select:
    - **If 'Based on random safety events'**:
        - The volume of the `Local Air Receiver` is multiplied by the `Safety Dump Events per Hour`.
    - **If 'After every machine cycle'**:
        - The volume of the `Local Air Receiver` is multiplied by the number of cycles per hour (`Machine Cycle Rate` * 60). This can be a very high cost!

    #### 3. ⚡ Servo System Cost
    - This is calculated from the motor's power rating and its average utilization, summed for all defined servos.
    """)

# --- Footer ---
st.markdown("---")
