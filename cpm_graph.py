import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def plot_gantt_chart(results, time_scale=7, language="English"):
    fig, ax = plt.subplots(figsize=(14, len(results) * 0.5))
    plt.title("Gantt Chart with Critical Path", fontsize=14)
    # Format x-axis ticks
    if time_scale == 1:
        major_locator = mdates.MonthLocator()
        minor_locator = mdates.DayLocator(interval=1)
        minor_fmt = mdates.DateFormatter("%d")
    elif time_scale == 7:
        major_locator = mdates.MonthLocator()
        minor_locator = mdates.DayLocator(interval=7)
        minor_fmt = mdates.DateFormatter("%d")
    else:
        major_locator = mdates.MonthLocator()
        minor_locator = mdates.DayLocator(interval=15)
        minor_fmt = mdates.DateFormatter("%d")

    if language == "Tiếng Việt":
        major_fmt = mdates.DateFormatter("Tháng %m")
        plt.title("Biểu đồ đường Gantt", fontsize=14)
    else:
        major_fmt = mdates.DateFormatter("%b")

    for i, row in results.iterrows():
        start = row['Start']
        end = row['End']
        duration = (end - start).days
        color = 'red' if row['Critical'] else 'steelblue'
        ax.barh(row['Name'], duration, left=start, height=0.5, color=color, edgecolor='black')
        ax.text(start + (end - start) / 2, i, row['ID'], va='center', ha='center', color='white', fontsize=8)

    ax.xaxis.set_major_locator(major_locator)
    ax.xaxis.set_major_formatter(major_fmt)
    ax.xaxis.set_minor_locator(minor_locator)
    ax.xaxis.set_minor_formatter(minor_fmt)


    ax.tick_params(axis='x', which='major', labelsize=10, pad=10)
    ax.tick_params(axis='x', which='minor', labelsize=8, rotation=90, pad=25)
    ax.invert_yaxis()
    ax.grid(True, which='major', axis='x', linestyle='--')
    

    return fig
