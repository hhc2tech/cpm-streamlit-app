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
st.title("\U0001F4CA CPM Scheduler with Advanced Constraints")

st.markdown("""
This app allows you to:
1. Upload or edit your project schedule.
2. Compute Critical Path using CPM.
3. Visualize the actual Start and End Dates from file.
4. Export report to PDF.
""")

# Load schedule data
def get_schedule():
    uploaded_file = st.file_uploader("\U0001F4C2 Upload CSV Schedule File", type=["csv"])
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

st.subheader("\U0001F4DD Input Schedule Data")
data = get_schedule()
filename = st.text_input("\U0001F4BE Enter filename to save CSV:", value="cpm_sample.csv")

st.markdown("**Select CPM Calculation Method:**")
method = st.radio("Use Start/End Dates or calculate by CPM logic:", ["Use CSV Start/End Dates", "Calculate by CPM Logic"])

data = st.data_editor(data, use_container_width=True, num_rows="dynamic")

if st.button("\U0001F4E5 Save Current Table to CSV"):
    csv = data.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Click to download", csv, file_name=filename, mime="text/csv")

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
        duration = graph.nodes[node].get('duration', 0)

        for pred in graph.predecessors(node):
            edge = graph.edges[pred, node]
            pred_es = es.get(pred, 0)
            pred_ef = ef.get(pred, 0)

            if edge['type'] == 'FS':
                es[node] = max(es[node], pred_ef + edge['lag'])
            elif edge['type'] == 'SS':
                es[node] = max(es[node], pred_es + edge['lag'])
            elif edge['type'] == 'FF':
                ef_candidate = pred_ef + edge['lag']
                es_candidate = ef_candidate - duration
                es[node] = max(es[node], es_candidate)
            elif edge['type'] == 'SF':
                ef_candidate = pred_es + edge['lag']
                es_candidate = ef_candidate - duration
                es[node] = max(es[node], es_candidate)

        ef[node] = es[node] + duration

lf, ls = {}, {}
if ef:
    end_node = max(ef, key=ef.get)
    project_duration = ef[end_node]

    for node in reversed(list(nx.topological_sort(graph))):
        lf[node] = project_duration
        duration = graph.nodes[node].get('duration', 0)

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

        ls[node] = lf[node] - duration
else:
    project_duration = 0

# Compile analysis results
results = []
start_origin = pd.to_datetime(data.loc[data['Predecessors'] == "", 'Start Date'].min(), dayfirst=True)

for _, row in data.iterrows():
    aid = str(row.get('Activity ID')).strip()
    if aid not in es or aid not in ls:
        continue
    tf = ls[aid] - es[aid]
    duration = graph.nodes[aid].get('duration', 0)

    if method == "Use CSV Start/End Dates" and pd.notna(row.get('Start Date')) and pd.notna(row.get('End Date')):
        start_date = pd.to_datetime(row['Start Date'], dayfirst=True)
        end_date = pd.to_datetime(row['End Date'], dayfirst=True)
    else:
        start_date = start_origin + pd.to_timedelta(es[aid], unit='D')
        end_date = start_origin + pd.to_timedelta(ef[aid], unit='D')

    results.append({
        'ID': aid,
        'Name': row.get('Activity Name', aid),
        'Duration': duration,
        'Start': start_date,
        'End': end_date,
        'Float': tf,
        'Critical': tf == 0
    })

results = pd.DataFrame(results)

st.subheader("\U0001F4CB CPM Analysis Results")
st.dataframe(results, use_container_width=True)

# Gantt chart time scale and language options
with st.expander("⚙️ Gantt Chart Display Options", expanded=True):
    language = st.selectbox("🌐 Select Language", ["English", "Tiếng Việt"], index=0)
    time_scale = st.selectbox("📏 Select Time Axis Scale (in days):", options=[1, 7, 15], index=1)

# Gantt Chart
fig = plot_gantt_chart(results, time_scale, language)
st.pyplot(fig)

# Export to PDF
if st.button("\U0001F4C4 Export Gantt Chart to PDF"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf_path = tmp_file.name
        fig.savefig(pdf_path, format="pdf")
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download Gantt PDF", f.read(), file_name="gantt_chart.pdf", mime="application/pdf")

# Summary
if not results.empty:
    critical_path = ' ➝ '.join(results[results['Critical']]['ID'])
    st.success(f"🔺 Critical Path: {critical_path}")
    st.info(f"📅 Total Project Duration: {project_duration} days")
