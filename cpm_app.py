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

st.set_page_config(page_title="CPM Scheduler", layout="wide")
st.title("📊 CPM Scheduler with Advanced Constraints")

st.markdown("""
This app allows you to:
1. Upload or edit your project schedule.
2. Compute Critical Path using CPM.
3. Visualize the actual Start and End Dates from file.
4. Export report to PDF.
""")

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
            "Start Date": ["01/04/2023", "01/04/2023", "06/04/2023", "21/04/2023", "05/06/2023"],
            "End Date": ["01/04/2023", "06/04/2023", "21/05/2023", "05/06/2023", "05/07/2023"]
        })
    return df

st.subheader("📝 Input Schedule Data")
data = get_schedule()
st.dataframe(data, use_container_width=True)

# Build graph with constraint types
graph = nx.DiGraph()
for _, row in data.iterrows():
    if 'Activity ID' not in row or pd.isna(row['Activity ID']):
        continue
    graph.add_node(row['Activity ID'], name=row.get('Activity Name', row['Activity ID']), duration=row.get('Duration', 0))
    constraints = parse_logic_constraints(row.get("Constraint", ""))
    if pd.notna(row.get('Predecessors', "")) and row['Predecessors'] != "":
        predecessors = [x.strip() for x in str(row['Predecessors']).split(',')]
        if not constraints:
            for pred in predecessors:
                graph.add_edge(pred, row['Activity ID'], type='FS', lag=0)
        else:
            for c in constraints:
                graph.add_edge(c['predecessor'], row['Activity ID'], type=c['type'], lag=c['lag'])

# Compute forward and backward passes
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
                es[node] = max(es[node], ef_val - graph.nodes[node]['duration'])
            elif edge['type'] == 'SF':
                ef_val = es[pred] + edge['lag']
                es[node] = max(es[node], ef_val - graph.nodes[node]['duration'])
        ef[node] = es[node] + graph.nodes[node]['duration']

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
        ls[node] = lf[node] - graph.nodes[node]['duration']
else:
    project_duration = 0

# Results
table = []
for _, row in data.iterrows():
    aid = row.get('Activity ID')
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

# Gantt Chart
st.subheader("📈 Gantt Chart")
fig, ax = plt.subplots(figsize=(14, len(results) * 0.5))
for i, row in results.iterrows():
    start = row['Start']
    duration = (row['End'] - row['Start']).days
    color = 'red' if row['Critical'] else 'steelblue'
    ax.barh(row['ID'] + ' - ' + row['Name'], duration, left=start, height=0.5, color=color, edgecolor='black')
    ax.text(start + timedelta(days=0.1), i, row['ID'], va='center', ha='left', color='white', fontsize=8)

ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=[1, 15]))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
ax.tick_params(axis='x', which='major', labelsize=10, pad=10)
ax.tick_params(axis='x', which='minor', labelsize=8, rotation=90)
ax.invert_yaxis()
ax.grid(True, which='major', axis='x', linestyle='--')
plt.title("Gantt Chart with Critical Path", fontsize=14)
st.pyplot(fig)

# Summary
if not results.empty:
    critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
    st.success(f"🔺 Critical Path: {critical_path}")
    st.info(f"📅 Total Project Duration: {project_duration} days")
