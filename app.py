import streamlit as st
from database import initialize_database   #  run migrations first
initialize_database()

from views.project_view import show_project_view

# ––– Streamlit page setup –––
st.set_page_config(page_title="Collaborative CPM Tool",
                   page_icon="🏗️",
                   layout="wide")

st.title("🏗️ Collaborative Renovation Project Hub II")
st.markdown(
    """
Welcome! This is your central hub for managing the renovation project.  
All data is **saved to a persistent database** when you press the
*Save Schedule and Calculate Critical Path* button.
"""
)

# ––– Main UI –––
show_project_view()
