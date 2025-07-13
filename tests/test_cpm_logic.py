import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cpm_logic import calculate_cpm


def test_calculate_cpm_chain():
    df = pd.DataFrame({
        'Task ID': ['A', 'B', 'C'],
        'Task Name': ['A', 'B', 'C'],
        'Duration': [2, 2, 2],
        'Predecessors': ['', 'A', 'B']
    })
    result = calculate_cpm(df).set_index('Task ID')

    assert result.loc['A', 'ES'] == 1
    assert result.loc['A', 'EF'] == 2
    assert result.loc['A', 'LS'] == 1
    assert result.loc['A', 'LF'] == 2

    assert result.loc['B', 'ES'] == 3
    assert result.loc['B', 'EF'] == 4
    assert result.loc['B', 'LS'] == 3
    assert result.loc['B', 'LF'] == 4

    assert result.loc['C', 'ES'] == 5
    assert result.loc['C', 'EF'] == 6
    assert result.loc['C', 'LS'] == 5
    assert result.loc['C', 'LF'] == 6


def test_calculate_cpm_branching():
    df = pd.DataFrame({
        'Task ID': ['A', 'B', 'C', 'D'],
        'Task Name': ['A', 'B', 'C', 'D'],
        'Duration': [3, 2, 4, 1],
        'Predecessors': ['', 'A', 'A', 'B,C']
    })
    result = calculate_cpm(df).set_index('Task ID')

    # Task A
    assert result.loc['A', 'ES'] == 1
    assert result.loc['A', 'EF'] == 3
    assert result.loc['A', 'LS'] == 1
    assert result.loc['A', 'LF'] == 3

    # Task B
    assert result.loc['B', 'ES'] == 4
    assert result.loc['B', 'EF'] == 5
    assert result.loc['B', 'LS'] == 6
    assert result.loc['B', 'LF'] == 7

    # Task C
    assert result.loc['C', 'ES'] == 4
    assert result.loc['C', 'EF'] == 7
    assert result.loc['C', 'LS'] == 4
    assert result.loc['C', 'LF'] == 7

    # Task D
    assert result.loc['D', 'ES'] == 8
    assert result.loc['D', 'EF'] == 8
    assert result.loc['D', 'LS'] == 8
    assert result.loc['D', 'LF'] == 8
