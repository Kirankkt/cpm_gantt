# cpm_logic.py
import pandas as pd

def calculate_cpm(df):
    """
    Performs the Critical Path Method calculations.
    - Forward Pass for Early Start (ES) and Early Finish (EF)
    - Backward Pass for Late Start (LS) and Late Finish (LF)
    - Calculates Float and identifies the Critical Path
    """
    # Ensure Duration is numeric
    df['Duration'] = pd.to_numeric(df['Duration'])

    # Initialize columns
    df['ES'] = 0
    df['EF'] = 0
    df['LS'] = 0
    df['LF'] = 0

    # Create a dictionary for easy predecessor lookup
    tasks = df['Task ID'].tolist()
    predecessors_map = {task: pred.split(',') if pred else [] for task, pred in zip(df['Task ID'], df['Predecessors'])}

    # --- Forward Pass ---
    for task in tasks:
        task_index = df.index[df['Task ID'] == task][0]
        preds = predecessors_map[task]
        
        if not preds or all(p == '' for p in preds):
            df.loc[task_index, 'ES'] = 1 # Start day 1
        else:
            max_ef_of_preds = 0
            for p_id in preds:
                p_id = p_id.strip()
                if p_id in df['Task ID'].values:
                    pred_ef = df.loc[df['Task ID'] == p_id, 'EF'].iloc[0]
                    if pred_ef > max_ef_of_preds:
                        max_ef_of_preds = pred_ef
            df.loc[task_index, 'ES'] = max_ef_of_preds + 1
            
        df.loc[task_index, 'EF'] = df.loc[task_index, 'ES'] + df.loc[task_index, 'Duration'] - 1

    # --- Backward Pass ---
    project_finish_time = df['EF'].max()
    df['LF'] = project_finish_time
    df['LS'] = df['LF'] - df['Duration'] + 1

    for task in reversed(tasks):
        task_index = df.index[df['Task ID'] == task][0]
        
        # Find successors of the current task
        successors = [t for t, preds in predecessors_map.items() if task in [p.strip() for p in preds]]
        
        if not successors:
            df.loc[task_index, 'LF'] = project_finish_time
        else:
            min_ls_of_successors = float('inf')
            for s_id in successors:
                succ_ls = df.loc[df['Task ID'] == s_id, 'LS'].iloc[0]
                if succ_ls < min_ls_of_successors:
                    min_ls_of_successors = succ_ls
            df.loc[task_index, 'LF'] = min_ls_of_successors - 1
            
        df.loc[task_index, 'LS'] = df.loc[task_index, 'LF'] - df.loc[task_index, 'Duration'] + 1

    # --- Calculate Float and Critical Path ---
    df['Float'] = df['LS'] - df['ES']
    df['On Critical Path?'] = df['Float'].apply(lambda x: 'Yes' if x == 0 else 'No')

    return df