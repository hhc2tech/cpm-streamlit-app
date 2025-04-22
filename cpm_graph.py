
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta

def plot_gantt_chart(results, time_scale):
    date_locator = mdates.DayLocator(interval=time_scale)
    fig, ax = plt.subplots(figsize=(14, len(results) * 0.5))
    for i, row in results.iterrows():
        start = row['Start']
        duration = (row['End'] - row['Start']).days
        color = 'red' if row['Critical'] else 'steelblue'
        ax.barh(row['Name'], duration, left=start, height=0.5, color=color, edgecolor='black')

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_minor_locator(date_locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
    ax.tick_params(axis='x', which='major', labelsize=10, pad=10)
    ax.tick_params(axis='x', which='minor', labelsize=8, rotation=90)
    ax.invert_yaxis()
    ax.grid(True, which='major', axis='x', linestyle='--')
    plt.title("Gantt Chart with Critical Path", fontsize=14)
    return fig
