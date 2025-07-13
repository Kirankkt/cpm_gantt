import pandas as pd
from sqlalchemy import create_engine, inspect, text

# --- DATABASE SETUP ---
DB_FILE = "projects.db"
engine = create_engine(f"sqlite:///{DB_FILE}")

def initialize_database():
    """
    Initializes the database. It creates the database file and the 'tasks' table
    if they don't already exist. This runs only once.
    """
    with engine.connect() as connection:
        if not inspect(engine).has_table("tasks"):
            connection.execute(text("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    task_id_str TEXT NOT NULL,
                    description TEXT NOT NULL,
                    predecessors TEXT,
                    duration INTEGER NOT NULL,
                    UNIQUE(project_id, task_id_str)
                );
            """))
            print("Database initialized and 'tasks' table created.")

def get_project_data_from_db(project_id=1):
    """
    This function reads the project data from the database and returns it
    as a pandas DataFrame, which our app knows how to work with.
    """
    query = text("""
        SELECT 
            task_id_str as "Task ID", 
            description as "Task Description", 
            predecessors as "Predecessors", 
            duration as "Duration" 
        FROM tasks 
        WHERE project_id = :proj_id
    """)
    with engine.connect() as connection:
        df = pd.read_sql(query, connection, params={"proj_id": project_id})
    return df

def save_project_data_to_db(df, project_id=1):
    """
    This function saves the edited DataFrame from the Streamlit app
    back into our database.
    """
    # This function is now a wrapper around the new import function for clarity.
    import_df_to_db(df, project_id)
    print("Project data saved to database.")

# --- NEW FUNCTION FOR IMPORTING ---
def import_df_to_db(df, project_id=1):
    """
    Imports a DataFrame into the database, overwriting any existing data for the project.
    This is perfect for handling file uploads.
    """
    df_to_save = df.copy()
    
    # Ensure standard required columns exist
    required_cols = ["Task ID", "Task Description", "Predecessors", "Duration"]
    for col in required_cols:
        if col not in df_to_save.columns:
            raise ValueError(f"Uploaded file is missing required column: {col}")

    df_to_save['project_id'] = project_id
    
    # Rename columns to match our database table schema
    df_to_save = df_to_save.rename(columns={
        "Task ID": "task_id_str",
        "Task Description": "description",
        "Predecessors": "predecessors",
        "Duration": "duration"
    })
    
    # Select only the columns that match the database table to avoid errors
    db_cols = ["project_id", "task_id_str", "description", "predecessors", "duration"]
    df_to_save = df_to_save[db_cols]

    with engine.connect() as connection:
        # Strategy: Delete all old tasks for this project before inserting new ones.
        connection.execute(text("DELETE FROM tasks WHERE project_id = :proj_id"), {"proj_id": project_id})
        
        # Use pandas' to_sql() to efficiently insert all rows from the DataFrame.
        df_to_save.to_sql("tasks", con=connection, if_exists="append", index=False)
        
        connection.commit()
    print(f"Successfully imported {len(df_to_save)} tasks into the database.")