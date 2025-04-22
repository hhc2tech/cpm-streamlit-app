#refer: https://www.investopedia.com/terms/g/gantt-chart.asp
# data = st.data_editor(get_sample_data(), num_rows="dynamic", use_container_width=True)   row 28
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
from datetime import timedelta
from fpdf import FPDF
import tempfile
import os
from io import StringIO

st.set_page_config(page_title="CPM Scheduler", layout="wide")
st.title("📊 Critical Path Method (CPM) Scheduler")

st.markdown("""
This app allows you to:
1. Upload or edit your project schedule.
2. Automatically compute Critical Path using CPM.
3. Visualize the schedule and critical path using a classic Gantt chart.
4. Export the analysis to PDF.
5. View the Network Diagram.
""")

# Sample data from uploaded or default CSV
def get_schedule():
    uploaded_file = st.file_uploader("📂 Upload CSV Schedule File", type="csv")
    try:
        if uploaded_file:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            df = pd.read_csv(stringio)
        elif os.path.exists("investopedia_project_schedule.csv"):
            df = pd.read_csv("investopedia_project_schedule.csv")
        else:
            df = pd.DataFrame({
                "Activity ID": ["A"],
                "Activity Name": ["Sample Task"],
                "Duration": [5],
                "Predecessors": [""],
                "Start Date": ["2023-04-01"]
            })
    except Exception as e:
        st.error(f"❌ Error reading CSV: {e}")
        df = pd.DataFrame({
            "Activity ID": ["A"],
            "Activity Name": ["Sample Task"],
            "Duration": [5],
            "Predecessors": [""],
            "Start Date": ["2023-04-01"]
        })
    if 'Start Date' not in df.columns:
        df['Start Date'] = '2023-04-01'
    return df

st.subheader("📝 Input Schedule Data")
data = st.data_editor(get_schedule(), num_rows="dynamic", use_container_width=True)

# Graph construction
graph = nx.DiGraph()
for _, row in data.iterrows():
    graph.add_node(row['Activity ID'], name=row['Activity Name'], duration=row['Duration'])
    if pd.notna(row['Predecessors']) and row['Predecessors'].strip() != '':
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

# Gantt Chart
st.subheader("📈 Gantt Chart")
fig, ax = plt.subplots(figsize=(14, 8))
start_date = pd.to_datetime("2023-04-01")

for i, row in results.iterrows():
    start = start_date + timedelta(days=row['ES'])
    color = 'red' if row['Critical'] else 'steelblue'
    ax.barh(row['ID'] + ' - ' + row['Name'], row['Duration'], left=start, height=0.5, color=color, edgecolor='black')
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

# Network Diagram
st.subheader("📌 Network Diagram")
fig2, ax2 = plt.subplots(figsize=(14, 8))
pos = nx.spring_layout(graph, seed=42)
nx.draw(graph, pos, with_labels=True, node_color='skyblue', node_size=2000, font_size=10, font_weight='bold', ax=ax2)
st.pyplot(fig2)

# PDF Export
st.subheader("📤 Export Report")
if st.button("Download PDF Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Critical Path Method Analysis Report", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for i, row in results.iterrows():
        line = f"{row['ID']} - {row['Name']} | Dur: {row['Duration']} | ES: {row['ES']} | EF: {row['EF']} | LS: {row['LS']} | LF: {row['LF']} | Float: {row['Float']} | Critical: {row['Critical']}"
        pdf.multi_cell(0, 8, txt=line)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        with open(tmp_file.name, "rb") as f:
            st.download_button("📄 Download PDF", data=f, file_name="CPM_Report.pdf")

# Summary
critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
st.success(f"🔺 Critical Path: {critical_path}")
st.info(f"📅 Total Project Duration: {project_duration} days")
