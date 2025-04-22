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
            df = pd.read_csv(stringio, sep=';', dayfirst=True)
        elif os.path.exists("design_schedule_updated.csv"):
            df = pd.read_csv("design_schedule_updated.csv", sep=';', dayfirst=True)
        else:
            df = pd.DataFrame({
                "Activity ID": ["A"],
                "Activity Name": ["Sample Task"],
                "Duration": [5],
                "Predecessors": [""],
                "Constraint": [""],
                "Start Date": ["01/04/2023"],
                "End Date": ["05/04/2023"]
            })
    except Exception as e:
        st.error(f"❌ Error reading CSV: {e}")
        df = pd.DataFrame({
            "Activity ID": ["A"],
            "Activity Name": ["Sample Task"],
            "Duration": [5],
            "Predecessors": [""],
            "Constraint": [""],
            "Start Date": ["01/04/2023"],
            "End Date": ["05/04/2023"]
        })
    return df

st.subheader("📝 Input Schedule Data")
data = st.data_editor(get_schedule(), num_rows="dynamic", use_container_width=True)

# Build graph with constraint types
graph = nx.DiGraph()
for _, row in data.iterrows():
    graph.add_node(row['Activity ID'], name=row['Activity Name'], duration=row['Duration'])
    constraints = parse_logic_constraints(row.get("Constraint", ""))
    if pd.notna(row['Predecessors']) and row['Predecessors'] != "":
        predecessors = [x.strip() for x in row['Predecessors'].split(',')]
        if not constraints:
            for pred in predecessors:
                graph.add_edge(pred, row['Activity ID'], type='FS', lag=0)
        else:
            for c in constraints:
                graph.add_edge(c['predecessor'], row['Activity ID'], type=c['type'], lag=c['lag'])

# Compute forward and backward passes
es, ef = {}, {}
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

# Results
table = []
for _, row in data.iterrows():
    aid = row['Activity ID']
    tf = ls[aid] - es[aid]
    table.append({
        'ID': aid,
        'Name': row['Activity Name'],
        'Duration': row['Duration'],
        'Start': pd.to_datetime(row['Start Date'], dayfirst=True),
        'End': pd.to_datetime(row['End Date'], dayfirst=True),
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
critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
st.success(f"🔺 Critical Path: {critical_path}")
st.info(f"📅 Total Project Duration: {project_duration} days")
