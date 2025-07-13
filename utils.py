# utils.py
import pandas as pd

def get_sample_data():
    """
    Returns a sample project plan as a Pandas DataFrame.
    """
    data = {
        'Task ID': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
        'Task Description': [
            'Initial Planning', 'Site Preparation', 'Foundation', 'Framing',
            'Plumbing & Electrical', 'Drywall & Interior', 'Exterior Finishes', 'Final Inspection'
        ],
        'Predecessors': [
            '', 'A', 'B', 'C', 'C', 'D,E', 'D', 'F,G'
        ],
        'Duration': [5, 10, 15, 20, 12, 18, 9, 3],
        'Start Date': [None] * 8
    }
    df = pd.DataFrame(data)
    return df
