# Collaborative CPM Tool

This application provides a simple interface for planning and analysing projects using the Critical Path Method (CPM). It is built with [Streamlit](https://streamlit.io/) and uses Plotly for the interactive Gantt chart.

## Installation

1. Clone the repository and change into the project directory.
2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

Start the Streamlit application with:

```bash
streamlit run app.py
```

You can change where the SQLite database is stored by setting the
`DATABASE_PATH` environment variable before starting the app. By default the
file `projects.db` will be created in the project directory.

The web interface lets you enter tasks, durations and dependencies directly in your browser. You can also import a CSV file with the task list or export results after calculation.

## Features

- **Persistent database** – tasks are stored in an SQLite database.
- **Data editing** – edit the task table inline or import a CSV file.
- **CPM calculations** – compute early/late start and finish dates, float and the critical path.
- **Project summary** – see total duration and the list of critical tasks.
- **Interactive Gantt chart** – visualise the schedule with tasks coloured by critical path status.
- **Export** – download the full schedule as a CSV file.

## About CPM and the Gantt Chart

The **Critical Path Method** is a technique for analysing task dependencies to determine the minimum time required to complete a project. By calculating early and late start/finish values, the method identifies tasks with zero float – these form the **critical path** and cannot be delayed without affecting the project end date.

After running the calculation, the application displays an interactive **Gantt chart**. Each bar represents a task, positioned along a timeline based on its early start and finish. Tasks on the critical path are highlighted, providing a clear visual overview of the schedule.


## Running Tests

Unit tests use [pytest](https://pytest.org). After installing dependencies, run:

```bash
pytest
```

