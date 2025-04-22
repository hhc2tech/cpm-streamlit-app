import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
from datetime import timedelta, datetime
from fpdf import FPDF
import tempfile
import os
from io import StringIO
from constraints import parse_logic_constraints
from cpm_graph import plot_gantt_chart

st.set_page_config(page_title="CPM Scheduler", layout="wide")
st.title("📊 CPM Scheduler with Advanced Constraints")

st.markdown("""
This app allows you to:
1. Upload or edit your project schedule.
2. Compute Critical Path using CPM.
3. Visualize the actual Start and End Dates from file.
4. Export report to PDF.
""")

# Load schedule data
def get_schedule():
    uploaded_file = st.file_uploader("📂 Upload CSV Schedule File", type=["csv"])
    try:
        if uploaded_file:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            df = pd.read_csv(stringio, sep=None, engine='python')
        elif os.path.exists("design_schedule0.csv"):
            df = pd.read_csv("design_schedule0.csv", sep=None, engine='python')
        else:
            raise FileNotFoundError("No valid schedule file found.")
        df.columns = df.columns.str.strip()
    except Exception as e:
        st.error(f"❌ Error reading CSV: {e}")
        df = pd.DataFrame({
            "Activity ID": ["T1", "T2", "T3", "T4", "T5"],
            "Activity Name": [
                "Thương thảo và ký hợp đồng",
                "chuẩn bị",
                "Khảo sát địa hình",
                "Khảo sát địa chất (hiện trường)",
                "Thí nghiệm trong phòng"
            ],
            "Duration": [5, 5, 45, 45, 30],
            "Predecessors": ["", "T1", "T2", "T2", "T4"],
            "Constraint": ["", "", "", "FS+15", ""],
            "Start Date": ["01/04/2023", "06/04/2023", "11/04/2023", "26/04/2023", "10/06/2023"],
            "End Date": ["06/04/2023", "11/04/2023", "26/05/2023", "10/06/2023", "10/07/2023"]
        })
    return df.reset_index(drop=True)

st.subheader("📝 Input Schedule Data")
data = get_schedule()
filename = st.text_input("💾 Enter filename to save CSV:", value="cpm_sample.csv")
data = st.data_editor(data, use_container_width=True, num_rows="dynamic")

if st.button("📥 Save Current Table to CSV"):
    csv = data.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Click to download", csv, file_name=filename, mime='text/csv')

# Build project graph
graph = nx.DiGraph()
for _, row in data.iterrows():
    aid = str(row.get('Activity ID')).strip()
    if not aid:
        continue
    graph.add_node(aid, name=row.get('Activity Name', aid), duration=row.get('Duration', 0))
    constraints = parse_logic_constraints(str(row.get("Constraint", "") or ""))
    if pd.notna(row.get('Predecessors', "")) and row['Predecessors'] != "":
        predecessors = [x.strip() for x in str(row['Predecessors']).split(',') if x.strip() != '']
        if not constraints:
            for pred in predecessors:
                graph.add_edge(pred, aid, type='FS', lag=0)
        else:
            for c in constraints:
                graph.add_edge(c['predecessor'], aid, type=c['type'], lag=c['lag'])

# Check for cycles before CPM calculation
try:
    cycle_check = list(nx.find_cycle(graph, orientation='original'))
    if cycle_check:
        st.error("⚠️ Your schedule has a circular dependency (logic loop). Please fix before continuing.")
        st.stop()
except nx.NetworkXNoCycle:
    pass

# CPM calculation
es, ef = {}, {}
if len(graph.nodes) > 0:
    for node in nx.topological_sort(graph):
        es[node] = 0
        for pred in graph.predecessors(node):
            edge = graph.edges[pred, node]
            if edge['type'] == 'FS':
                es[node] = max(es[node], ef[pred] + edge['lag'])
            elif edge['type'] == 'SS':
                es[node] = max(es[node], es[pred] + edge['lag'])
            elif edge['type'] == 'FF':
                ef_val = ef[pred] + edge['lag']
                es[node] = max(es[node], ef_val - graph.nodes[node].get('duration', 0))
            elif edge['type'] == 'SF':
                ef_val = es[pred] + edge['lag']
                es[node] = max(es[node], ef_val - graph.nodes[node].get('duration', 0))
        ef[node] = es[node] + graph.nodes[node].get('duration', 0)

lf, ls = {}, {}
if ef:
    end_node = max(ef, key=ef.get)
    project_duration = ef[end_node]

    for node in reversed(list(nx.topological_sort(graph))):
        lf[node] = project_duration
        for succ in graph.successors(node):
            edge = graph.edges[node, succ]
            if edge['type'] == 'FS':
                lf[node] = min(lf[node], ls[succ] - edge['lag'])
            elif edge['type'] == 'SS':
                lf[node] = min(lf[node], ls[succ] - edge['lag'])
            elif edge['type'] == 'FF':
                lf[node] = min(lf[node], lf[succ] - edge['lag'])
            elif edge['type'] == 'SF':
                lf[node] = min(lf[node], es[succ] - edge['lag'])
        ls[node] = lf[node] - graph.nodes[node].get('duration', 0)
else:
    project_duration = 0

# Compile analysis results
table = []
for _, row in data.iterrows():
    aid = str(row.get('Activity ID')).strip()
    if aid not in es or aid not in ls:
        continue
    tf = ls[aid] - es[aid]
    table.append({
        'ID': aid,
        'Name': row.get('Activity Name', aid),
        'Duration': row.get('Duration', 0),
        'Start': pd.to_datetime(row.get('Start Date'), dayfirst=True),
        'End': pd.to_datetime(row.get('End Date'), dayfirst=True),
        'Float': tf,
        'Critical': tf == 0
    })

results = pd.DataFrame(table)

st.subheader("📋 CPM Analysis Results")
st.dataframe(results, use_container_width=True)

# Gantt chart time scale and language options
with st.expander("⚙️ Gantt Chart Display Options", expanded=True):
    language = st.selectbox("🌐 Select Language", ["English", "Tiếng Việt"], index=0)
    time_scale = st.selectbox("📏 Select Time Axis Scale (in days):", options=[1, 7, 15], index=1)

# Gantt Chart
fig = plot_gantt_chart(results, time_scale, language)
st.pyplot(fig)

# Summary
if not results.empty:
    critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
    st.success(f"🔺 Critical Path: {critical_path}")
    st.info(f"📅 Total Project Duration: {project_duration} days")
