# data = st.data_editor(get_sample_data(), num_rows="dynamic", use_container_width=True)   row 28

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
from datetime import timedelta

st.set_page_config(page_title="CPM Scheduler", layout="wide")
st.title("📊 Critical Path Method (CPM) Scheduler")

st.markdown("""
This app allows you to:
1. Upload or edit your project schedule.
2. Automatically compute Critical Path using CPM.
3. Visualize the schedule and critical path using a classic Gantt chart.
""")

# Sample data
def get_sample_data():
    return pd.DataFrame({
        'Activity ID': ['A', 'B', 'C', 'D', 'E'],
        'Activity Name': ['Excavation', 'Foundation', 'Framing', 'Electrical', 'Roofing'],
        'Duration': [5, 3, 4, 2, 3],
        'Predecessors': ['', 'A', 'B', 'B', 'C,D']
    })

st.subheader("📝 Input Schedule Data")
data = st.data_editor(get_sample_data(), num_rows="dynamic", use_container_width=True)

# Graph construction
graph = nx.DiGraph()
for _, row in data.iterrows():
    graph.add_node(row['Activity ID'], name=row['Activity Name'], duration=row['Duration'])
    if pd.notna(row['Predecessors']) and row['Predecessors'] != '':
        preds = [p.strip() for p in str(row['Predecessors']).split(',')]
        for pred in preds:
            graph.add_edge(pred, row['Activity ID'])

# Forward and Backward Pass
es, ef = {}, {}
for node in nx.topological_sort(graph):
    preds = list(graph.predecessors(node))
    es[node] = max([ef[p] for p in preds], default=0)
    ef[node] = es[node] + graph.nodes[node]['duration']

lf, ls = {}, {}
end_node = max(ef, key=ef.get)
project_duration = ef[end_node]
for node in reversed(list(nx.topological_sort(graph))):
    succs = list(graph.successors(node))
    lf[node] = min([ls[s] for s in succs], default=project_duration)
    ls[node] = lf[node] - graph.nodes[node]['duration']

# Results
table = []
for node in graph.nodes():
    tf = ls[node] - es[node]
    table.append({
        'ID': node,
        'Name': graph.nodes[node]['name'],
        'Duration': graph.nodes[node]['duration'],
        'ES': es[node],
        'EF': ef[node],
        'LS': ls[node],
        'LF': lf[node],
        'Float': tf,
        'Critical': tf == 0
    })

results = pd.DataFrame(table).sort_values(by='ES')
st.subheader("📋 CPM Analysis Results")
st.dataframe(results, use_container_width=True)

# Classic Gantt Chart (matplotlib)
st.subheader("📈 Gantt Chart")
fig, ax = plt.subplots(figsize=(12, 6))
start_date = pd.to_datetime("2023-01-01")

for i, row in results.iterrows():
    start = start_date + timedelta(days=row['ES'])
    end = start + timedelta(days=row['Duration'])
    color = 'red' if row['Critical'] else 'steelblue'
    ax.barh(row['ID'] + ' - ' + row['Name'], row['Duration'], left=start, height=0.5, color=color, edgecolor='black')
    ax.text(start + timedelta(days=0.1), i, row['ID'], va='center', ha='left', color='white', fontsize=8)

ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
ax.invert_yaxis()
ax.grid(True, which='major', axis='x', linestyle='--')
plt.title("Gantt Chart with Critical Path", fontsize=14)
st.pyplot(fig)

# Summary
critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
st.success(f"🔺 Critical Path: {critical_path}")
st.info(f"📅 Total Project Duration: {project_duration} days")
