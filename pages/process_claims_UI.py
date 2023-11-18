import streamlit as st
import openpyxl
import pandas as pd
from datetime import datetime
import time
import logging

st.title("App Calculating LACE Scores using Medicare Claims Data")
st.write("This app calculates LACE scores for patients based on a Medicare Claims Data file.")
claims_file = st.file_uploader("Upload current medicare claims file", ".csv", key="upload1")
prev_claims_files = st.file_uploader("Upload medicare claims files for the previous 6 months", ".csv", key="upload2")

# Current claims file gets processed by process_claims.py and the LAC (but not the E) part of the LACE index is calculated.
# Output should be [BENE_ID, LACE_SCORE] where LACE_SCORE is the LACE index of BENE_ID's latest visit.

# Previous claims files are used only to compute the LACE scores
