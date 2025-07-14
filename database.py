# database.py  –  persistent SQLite helpers
# =========================================
import os
import pathlib
import warnings
import tempfile
import pandas as pd
from sqlalchemy import create_engine, inspect, text

# ------------------------------------------------------------------
# Persistent DB lives in /mnt/data (writable on Streamlit Cloud)
# ------------------------------------------------------------------
DATA_DIR = pathlib.Path("/mnt/data")
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError as e:
    warnings.warn(f"{e} – falling back to a temp directory (NON-persistent)")
    DATA_DIR = pathlib.Path(tempfile.gettempdir())

DB_FILE = os.environ.get("DATABASE_PATH", str(DATA_DIR / "projects.db"))
engine  = create_engine(f"sqlite:///{DB_FILE}", echo=False)


# ------------------------------------------------------------------
# Schema creation & lightweight migrations
# ------------------------------------------------------------------
def initialize_database() -> None:
    """Create the tasks table (if missing) and run tiny migrations."""
    with engine.connect() as conn:
        if not inspect(engine).has_table("tasks"):
            conn.execute(text("""
                CREATE TABLE tasks (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id       INTEGER NOT NULL,
                    task_id_str      TEXT    NOT NULL,
                    description      TEXT    NOT NULL,
                    predecessors     TEXT,
                    duration         INTEGER NOT NULL,
                    start_date       TEXT,
                    percent_complete REAL    DEFAULT 0,
                    UNIQUE(project_id, task_id_str)
                );
            """))
            conn.commit()
            print("Database initialised and 'tasks' table created.")

        _ensure_all_columns()


def _ensure_all_columns() -> None:
    """Add any columns that older DB versions might be missing."""
    required = {
        "start_date":       "TEXT",
        "percent_complete": "REAL DEFAULT 0",
    }
    with engine.begin() as conn:
        existing = {c["name"] for c in inspect(conn).get_columns("tasks")}
        for col, ddl in required.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {ddl};"))
                print(f"Added missing column '{col}' to tasks table.")


# ------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------
def get_project_data_from_db(project_id: int = 1) -> pd.DataFrame:
    """Return tasks for one project as a DataFrame."""
    query = text("""
        SELECT task_id_str      AS "Task ID",
               description      AS "Task Description",
               predecessors     AS "Predecessors",
               duration         AS "Duration",
               start_date       AS "Start Date",
               percent_complete AS "Percent Complete"
        FROM tasks
        WHERE project_id = :proj_id
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"proj_id": project_id})

    if "Start Date" in df.columns:
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
    return df


def save_project_data_to_db(df: pd.DataFrame, project_id: int = 1) -> None:
    """Persist (overwrite) tasks for *project_id*."""
    import_df_to_db(df, project_id)
    print("Project data saved to database.")


def import_df_to_db(df: pd.DataFrame, project_id: int = 1) -> None:
    """
    Overwrite tasks for the project with rows from *df*.
    Adds Percent Complete if the column is missing.
    """
    required = [
        "Task ID",
        "Task Description",
        "Predecessors",
        "Duration",
        "Start Date",
    ]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Uploaded file is missing required column: {col}")

    df_to_save = df.copy()
    df_to_save["project_id"] = project_id

    # ensure progress column
    if "Percent Complete" not in df_to_save.columns:
        df_to_save["Percent Complete"] = 0

    # rename to DB column names
    df_to_save = df_to_save.rename(columns={
        "Task ID":          "task_id_str",
        "Task Description": "description",
        "Predecessors":     "predecessors",
        "Duration":         "duration",
        "Start Date":       "start_date",
        "Percent Complete": "percent_complete",
    })

    # normalise date + progress
    df_to_save["start_date"] = pd.to_datetime(df_to_save["start_date"]).dt.strftime("%Y-%m-%d")
    df_to_save["percent_complete"] = (
        pd.to_numeric(df_to_save["percent_complete"], errors="coerce")
        .fillna(0)
        .clip(0, 100)
    )

    # keep only DB columns
    db_cols = [
        "project_id",
        "task_id_str",
        "description",
        "predecessors",
        "duration",
        "start_date",
        "percent_complete",
    ]
    df_to_save = df_to_save[db_cols]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM tasks WHERE project_id = :p"),
                     {"p": project_id})
        df_to_save.to_sql("tasks", conn, if_exists="append", index=False)
