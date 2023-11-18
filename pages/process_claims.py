import streamlit as st
import openpyxl
import pandas as pd
from datetime import datetime
import time
import logging
logging.basicConfig(filename='log.txt', encoding='utf-8', level=logging.DEBUG)

EMERGENCY = True
NOT_EMERGENCY = False
PATIENT_DISCHARGE_STATUS_CODES = {"Still a patient": 30, "Discharged to other institution with inpatient care": 5, "Expired": 20}
comorbidities_from_icd_codes_RAW = {
        "Myocardial infarction": ["I21", "I22", "I25.2"],
        "Peripheral vascular disease": ["I70", "I71", "I73.1", "I73.8", "I73.9", "I77.1", "I79.0", "I79.2", "K55.1", "K55.8", "K55.9", "Z95.8", "Z95.9"], # Checked
        "Cerebrovascular disease": ["G45", "G46", "H34.0", ("I60", "I70")], # Checked
        "Diabetes without chronic complications": ["E10.0", "E10.1", "E10.6", "E10.8", "E10.9", 
            "E11.0", "E11.1", "E11.6","E11.8", "E11.9", "E12.0", "E12.1", "E12.6", "E12.8", "E12.9", 
            "E13.0", "E13.1", "E13.6", "E13.8", "E13.9", "E14.0", "E14.1", "E14.6", "E14.8", "E14.9"], # Checked
        
        "Heart failure": ["I09.9", "I11.0", "I13.0", "I13.2", "I25.5", "I42.0", ("I42.5", "I43"), "I43", "I50", "P29.0"],
        "Dementia": [("F00", "F04"), "F05.1", "G30", "G31.1"],
        "Chronic pulmonary disease": ["I27.8", "I27.9", ("J40", "J48"), ("J60", "J68"), "J68.4", "J70.1", "J70.3"], # Checked
        "Rheumatic disease": ["M05", "M06", "M31.5", ("M32", "M35"), "M35.1", "M35.3", "M36.0"],
        "Peptic ulcer disease": [("K25", "K29")], # Checked
        "Mild liver disease": ["B18", ("K70.0", "K70.4"), "K70.9", ("K71.3", "K71.6"), "K71.7", "K73", "K74", "K76.0", ("K76.2", "K76.5"), "K76.8", "K76.9", "Z94.4"],
        "Diabetes with chronic complications": [("E10.2", "E10.6"), "E10.7", ("E11.2", "E11.6"), "E11.7", ("E12.2", "E12.6"), "E12.7", ("E13.2", "E13.6"), "E13.7", ("E14.2", "E14.6"), "E14.7"],
        "Hemiplegia or paraplegia": ["G04.1", "G11.4", "G80.1", "G80.2", "G81", "G82", ("G83.0", "G83.5"), "G83.9"],
        "Renal disease (mild or moderate)": ["I12.9", "I13.0", "I13.10", "N03", "N05", ("N18.1", "N18.5"), "N18.9", "Z94.0"],
        "Renal disease (severe)": ["I12.0", "I13.11", "I13.2", "N18.5", "N18.6", "N19", "N25.0", "Z49", "Z99.2"],
        "Any malignancy": [("C00", "C27"), ("C30", "C35"), ("C37", "C42"), "C43", ("C45", "C59"), ("C60", "C77"), ("C81", "C86"), "C88", ("C90", "C98")],
        "Moderate or severe liver disease": ["I85.0", "I85.9", "I86.4", "I98.2", "K70.4", "K71.1", "K72.1", "K72.9", "K76.5", "K76.6", "K76.7"],
        "Metastatic solid tumor": [("C77", "C81")],
        "HIV": ["B20"],
        "AIDS": ["B37", "C53", "B38", "B45", "A07.2", "B25", "G93.4", "B00", "B39", "A07.3", "C46", ("C81", "C97"), "A31", ("A15", "A20"), "B59", "Z87.01", "A81.2", "A02.1", "B58", "R64"]
        # Checked all comorbities
    }
# @st.cache_data
def upload_and_process_file():
    # TODO Support fhir files, JSON?, RIF
    """
    Upload the user specified file (CSV only for now) and return a pandas dataframe. Currently only handles single file uploads
    """
    dev = False
    # TODO Generalize this to different file types and separators

    columns_to_use = ["BENE_ID", "CLM_ID", "CLM_IP_ADMSN_TYPE_CD", "REV_CNTR", "CLM_ADMSN_DT", 
                      "NCH_BENE_DSCHRG_DT", "PTNT_DSCHRG_STUS_CD", "PRNCPAL_DGNS_CD"]
    columns_to_use += ["ICD_DGNS_CD" + str(i) for i in range(1, 26)]
    if not dev:
        file = st.file_uploader("Upload medicare fee-for-service claim file(s):", accept_multiple_files=True, key="claims_upload")
        df = pd.read_csv(file, sep="|", low_memory = False, usecols=columns_to_use)
    else:
        df = pd.read_csv("inpatient.csv", sep = "|", low_memory = False, usecols=columns_to_use)
    return df
# I'm separating UI from logic. Working on logic now.
def acuity_of_admission(df_row):
    # print(df_row["REV_CNTR"])
    if df_row["CLM_IP_ADMSN_TYPE_CD"] in [1, 5]:
        return EMERGENCY
    elif 450 <= df_row["REV_CNTR"] <= 459 or df_row["REV_CNTR"] == 981:
        return EMERGENCY
    else:
        return NOT_EMERGENCY

def length_of_stay(df_row):
    """
    Calculate length of stay. Does not account for the case where the patient 
    """
    admsn_date, dschrg_date, dschrg_status = df_row["CLM_ADMSN_DT"], df_row["NCH_BENE_DSCHRG_DT"], df_row["PTNT_DSCHRG_STUS_CD"]
    admsn_date, dschrg_date = datetime.strptime(admsn_date, '%d-%b-%Y'), datetime.strptime(dschrg_date, '%d-%b-%Y')
    
    if dschrg_status == 30: # Patient is still a patient
        return
    elif dschrg_status == 20: # Patient died
        return
    elif dschrg_status == 5: # Patient transferred to different inpatient hospital
        return # We need the claims file from the different hospital and see how long the patient stayed there
    return dschrg_date - admsn_date

# TODO Add connective tissue disease codes
# Tested using unit tests
def get_charlson_comorbidity(icd_10_code):
    # Dictionary specifying comorbidities and corresponding icd 10 codes.
    # Ranges are in tuples (start, end) where the range is [start, end)

    if type(icd_10_code) != str:
        return []
    # Coding is consistent with http://mchp-appserv.cpe.umanitoba.ca/concept/Charlson%20Comorbidities%20-%20Coding%20Algorithms%20for%20ICD-9-CM%20and%20ICD-10.pdf 
    # For ICD-10 codes for renal disease and HIV/AIDS, see supplementary materials of https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6684052/. 
    # The decmials are stripped away from the dict entries to be consistent with the medicare claim file format

    # ARe these canadian codes or american codes? Read about ICD-10.
    comorbidities = {
        # Diseases with 1 point on comorbidity index
        "Myocardial infarction": ["I21", "I22", "I252"],
        "Peripheral vascular disease": ["I70", "I71", "I731", "I738", "I739", "I771", "I790", "I791", "I798", "K551", "K558", "K559", "Z958", "Z959"], # Checked
        "Cerebrovascular disease": ["G45", "G46", "H340", "H341", "H342", ("I60", "I69")], # Checked
        "Diabetes without chronic complications": ["E080", "E081", "E086", "E088", "E089", 
                                                   "E090", "E091", "E096", "E098", "E099",
                                                   "E100", "E101", "E106", "E108", "E109",
                                                   "E110", "E111", "E116", "E118", "E119",
                                                   "E130", "E131", "E136", "E138", "E139"],
        
        # Diseases with 2 pts on comorbidity index
        "Heart failure": ["I110", "I130", "I132", "I255", "I420", ("I425", "I43"), "I43", "I50", "P290"],
        "Chronic pulmonary disease": [("J40", "J48"), ("J60", "J68"), "J684", "J701", "J703"], # Checked
        "Mild liver disease": ["B18", ("K700", "K704"), "K70.9", ("K713", "K716"), "K717", "K73", "K74", "K760", ("K762", "K765"), "K768", "K769", "Z944"],
        "Diabetes with chronic complications": ["E082", "E083", "E084", "E085", 
                                                "E092", "E093", "E094", "E095", 
                                                "E102", "E103", "E104", "E105", 
                                                "E112", "E113", "E114", "E115", 
                                                "E132", "E133", "E134", "E135"],
        "Renal disease (mild or moderate)": ["I129", "I130", "I1310", "N03", "N05", ("N181", "N185"), "N189", "Z940"],
        "Any malignancy": [("C0", "C76"), ("C81", "C98")],
        
        # Diseases with 3 pts on comorbidity index.
        "Connective tissue disease": [("M30", "M37")], #TODO
        "Dementia": [("F01", "F06"), "F061", "F068", "G132", "G138", "G30", ("G310", "G313"), "G914", "G94", "R4181"], # Didn't include R54 as it's not specific to dementia
        
        # Diseases with 4+ points on comorbidity index.
        "Renal disease (severe)": ["I120", "I1311", "I132", "N185", "N186", "N19", "N250", "Z49", "Z992"],
        "Moderate or severe liver disease": ["I850", "I864", "K704", "K711", "K721", "K729", "K765", "K766", "K767"],
        "AIDS": ["A021", "A072", "A073", ("A15", "A20"), "A31", "A812",
                 "B00", "B25", "B37", "B38", "B39", "B45", "B58", "B59",
                 "C46", "C53", ("C81", "C97"), 
                 "G934", 
                 "R64", 
                 "Z8701"],
        "Metastatic solid tumor": [("C77", "C81")], 
        
        # Diseases currently with 0 points on comorbidity index for LACE
        # but could change in future versions
        "Rheumatic disease": ["M05", "M06", "M315", ("M32", "M35"), "M351", "M353", "M360"],
        "Peptic ulcer disease": [("K25", "K29")],
        "Hemiplegia or paraplegia": ["G041", "G114", "G800", "G801", "G802", "G81", "G82", "G83"],
        "HIV": ["B20"]
    }
    conditions = []
    for comorbidity, codes in comorbidities.items():
        for code in codes:
            if isinstance(code, tuple):
                start, end = code
                if start <= icd_10_code < end:
                    conditions.append(comorbidity)
            elif icd_10_code.startswith(code):
                    conditions.append(comorbidity)
    return conditions
# TODO: Add procedure codes to this. Add ICD codes for connective tissue disease
def get_all_charlson_comorbidities(df_row):
    """
    Input <- row from inpatient medicare claims file.
    output <- list of patient's charlson's comorbidities
    """
    comorbidity_columns = ["PRNCPAL_DGNS_CD"] # Refine
    comorbidity_columns += ["ICD_DGNS_CD" + str(i) for i in range(1, 26)]
    charlson_comorbidities = []
    for col in comorbidity_columns:
        try:
            code = df_row[col]
        except:
            logging.info("Column doesn't exist in dataframe")
            # Log code doesn't exist
            continue
        comorbidity = get_charlson_comorbidity(code)
        charlson_comorbidities += list(comorbidity)
    charlson_comorbidities = set(charlson_comorbidities)
        
    priorities = [("Metastatic solid tumor", "Any malignancy"), 
                  ("Diabetes with chronic complications", "Diabetes without chronic complications"), 
                  ("Moderate or severe liver disease", "Mild liver disease"), 
                  ("AIDS", "HIV"), 
                  ("Renal disease (severe)", "Renal disease (mild or moderate)")] # Fix
    for high_priority, low_priority in priorities: # if both high priority (i.e., severity) and low priority (less severe version) of the disease are listed, only keep the more severe (higher priority) disease version
        if high_priority in charlson_comorbidities:
            charlson_comorbidities.discard(low_priority)
    if "HIV" not in charlson_comorbidities: # AIDS = HIV + opportunistic infection; someone could have invasive cervical cancer without HIV and that's not AIDS.
        charlson_comorbidities.discard("AIDS")
    charlson_comorbidities.discard(None)
    return list(charlson_comorbidities)

def get_comorbidity_index_from_disease_list(disease_lst):
    comorbidity_scores = {
        "Myocardial infarction": 1,
        "Peripheral vascular disease": 1,
        "Cerebrovascular disease": 1,
        "Diabetes without chronic complications": 1,

        "Heart failure": 2,
        "Chronic pulmonary disease": 2,
        "Mild liver disease": 2,
        "Diabetes with chronic complications": 2,
        "Renal disease (mild or moderate)": 2,
        "Any malignancy": 2,
        
        "Connective tissue disease": 3,
        "Dementia": 3,

        "Renal disease (severe)": 4,
        "Moderate or severe liver disease": 4,
        "AIDS": 4,
        "Metastatic solid tumor": 6,
    }
    total_comorbidity_score = 0
    for comorbidity in disease_lst:
        total_comorbidity_score += comorbidity_scores.get(comorbidity, 0)
    return total_comorbidity_score

def get_comorbidities_score(df_row):
    charlson_comorbidities = get_all_charlson_comorbidities(df_row)
    total_comorbidity_score = get_comorbidity_index_from_disease_list(charlson_comorbidities)
    return total_comorbidity_score

def upload_and_process_outpatient_files():
    # Specify date
    columns_to_use = ["BENE_ID", "CLM_ID", "CLM_IP_ADMSN_TYPE_CD", "REV_CNTR", "CLM_ADMSN_DT"]
    
    files = st.file_uploader("Upload outpatient files for the previous 6 months.", 
                             accept_multiple_files=True, key="outpatient_files")
def main():

    # Initialize variables
    initial_time = time.time()
    df = upload_and_process_file()
    num_rows_inpatient_df = len(df.axes[0])
    hospital_stay_durations, hospital_admission_acuities = [], []
    comorbidities_list, comorbidity_scores_list = [], []
    emergency_dept_use = []
    beneficiaries = set()
    # Calculate L, A, and C
    for index, row in df.iterrows():
        beneficiaries.add(row["BENE_ID"])
        los = length_of_stay(row)
        acuity = acuity_of_admission(row)
        comorbidities = get_all_charlson_comorbidities(row)
        charlson_score = get_comorbidity_index_from_disease_list(comorbidities)

        hospital_stay_durations.append(los)
        hospital_admission_acuities.append(acuity)
        comorbidities_list.append(comorbidities)
        comorbidity_scores_list.append(charlson_score)

    # For debugging purposes. Will, in the final program, output the 
    # BENE_IDs along with their LACE scores and additional details
    df_new = df.assign(
        Length_of_stay=hospital_stay_durations, 
        Emergency_Admission=hospital_admission_acuities,
        Comorbidities=comorbidities_list,
        Comorbidity_Index=comorbidity_scores_list
    )
    df_new.to_csv('inpatient_with_lace_scores.csv', index=False)

    # Calculate E
    # Current file: Get beneficiary lists
    # New file: Get beneficiary ID and ER visits (duplicates allowed) and 
    # date (don't count the ER visit of the beneficiary before current admission)
    end_time = time.time()
    print(end_time - initial_time)

    
def test_acuity():
    df = upload_and_process_file()
    count = 1
    for index, row in df.iterrows():
        val = row["CLM_IP_ADMSN_TYPE_CD"]
        print(val, acuity_of_admission(row))
        count -= 1
        if count == 0: break

if __name__ == '__main__':
    # test_acuity()
    main()