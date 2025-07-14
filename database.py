import os
import pathlib
import pandas as pd
from sqlalchemy import create_engine, inspect, text

# ------------------------------------------------------------------
# Persistent DB: /mnt/data is the writable volume
# ------------------------------------------------------------------
DB_FILE = os.environ.get("DATABASE_PATH", "/mnt/data/projects.db")
engine  = create_engine(f"sqlite:///{DB_FILE}", echo=False)




# ------------------------------------------------------------------ #
#  Schema creation and lightweight migrations                        #
# ------------------------------------------------------------------ #
def initialize_database() -> None:
    """Create the tasks table (if missing) and run tiny migrations."""
    with engine.connect() as conn:
        if not inspect(engine).has_table("tasks"):
            conn.execute(text("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id   INTEGER NOT NULL,
                    task_id_str  TEXT    NOT NULL,
                    description  TEXT    NOT NULL,
                    predecessors TEXT,
                    duration     INTEGER NOT NULL,
                    start_date   TEXT,
                    UNIQUE(project_id, task_id_str)
                );
            """))
            conn.commit()
            print("Database initialised and 'tasks' table created.")

        _ensure_all_columns()

def _ensure_all_columns() -> None:
    """Add any columns that older DB versions might be missing."""
    required = {"start_date": "TEXT"}
    with engine.begin() as conn:
        existing = {col["name"] for col in inspect(conn).get_columns("tasks")}
        for col, ddl in required.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {ddl};"))
                print(f"Added missing column '{col}' to tasks table.")

# ------------------------------------------------------------------ #
#  Public helpers                                                    #
# ------------------------------------------------------------------ #
def get_project_data_from_db(project_id: int = 1) -> pd.DataFrame:
    """Return tasks for one project as a DataFrame."""
    query = text("""
        SELECT task_id_str  AS "Task ID",
               description  AS "Task Description",
               predecessors AS "Predecessors",
               duration     AS "Duration",
               start_date   AS "Start Date"
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
    """Overwrite tasks for the project with rows from *df*."""
    required = ["Task ID", "Task Description", "Predecessors", "Duration", "Start Date"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Uploaded file is missing required column: {col}")

    df_to_save             = df.copy()
    df_to_save["project_id"] = project_id

    df_to_save = df_to_save.rename(columns={
        "Task ID":         "task_id_str",
        "Task Description":"description",
        "Predecessors":    "predecessors",
        "Duration":        "duration",
        "Start Date":      "start_date"
    })

    df_to_save["start_date"] = pd.to_datetime(df_to_save["start_date"]).dt.strftime("%Y-%m-%d")

    db_cols = ["project_id", "task_id_str", "description",
               "predecessors", "duration", "start_date"]
    df_to_save = df_to_save[db_cols]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM tasks WHERE project_id = :p"),
                     {"p": project_id})
        df_to_save.to_sql("tasks", conn, if_exists="append", index=False)
