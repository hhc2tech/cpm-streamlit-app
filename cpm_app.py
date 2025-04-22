
import streamlit as st
import pandas as pd
import plotly.express as px
import networkx as nx

st.set_page_config(page_title="CPM Scheduler", layout="wide")
st.title("📊 Critical Path Method (CPM) Scheduler")

st.markdown("""
This app allows you to:
1. Upload or edit your project schedule.
2. Automatically compute Critical Path using CPM.
3. Visualize the schedule and critical path using a Gantt chart.
""")

# Sample default data
def get_sample_data():
    return pd.DataFrame({
        'Activity ID': ['A', 'B', 'C', 'D', 'E'],
        'Activity Name': ['Excavation', 'Foundation', 'Framing', 'Electrical', 'Roofing'],
        'Duration': [5, 3, 4, 2, 3],
        'Predecessors': ['', 'A', 'B', 'B', 'C,D']
    })

# Editable table
st.subheader("📝 Input Schedule Data")
data = st.experimental_data_editor(get_sample_data(), num_rows="dynamic", use_container_width=True)

# Build DAG
graph = nx.DiGraph()
for _, row in data.iterrows():
    graph.add_node(row['Activity ID'], name=row['Activity Name'], duration=row['Duration'])
    if pd.notna(row['Predecessors']) and row['Predecessors'] != '':
        preds = [p.strip() for p in str(row['Predecessors']).split(',')]
        for pred in preds:
            graph.add_edge(pred, row['Activity ID'])

# Forward Pass
es, ef = {}, {}
for node in nx.topological_sort(graph):
    preds = list(graph.predecessors(node))
    es[node] = max([ef[p] for p in preds], default=0)
    ef[node] = es[node] + graph.nodes[node]['duration']

# Backward Pass
lf, ls = {}, {}
end_node = max(ef, key=ef.get)
project_duration = ef[end_node]

for node in reversed(list(nx.topological_sort(graph))):
    succs = list(graph.successors(node))
    lf[node] = min([ls[s] for s in succs], default=project_duration)
    ls[node] = lf[node] - graph.nodes[node]['duration']

# Compile results
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

# Gantt Chart
gantt_data = pd.DataFrame({
    'Task': [f"{row['ID']} - {row['Name']}" for _, row in results.iterrows()],
    'Start': [row['ES'] for _, row in results.iterrows()],
    'Finish': [row['EF'] for _, row in results.iterrows()],
    'Critical': [row['Critical'] for _, row in results.iterrows()]
})

fig = px.timeline(gantt_data, x_start='Start', x_end='Finish', y='Task', color='Critical',
                  title='Gantt Chart - Critical Path Highlighted', height=500)
fig.update_yaxes(autorange="reversed")

st.subheader("📈 Gantt Chart")
st.plotly_chart(fig, use_container_width=True)

# Summary
critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
st.success(f"🔺 Critical Path: {critical_path}")
st.info(f"📅 Total Project Duration: {project_duration} days")
