import streamlit as st
import openpyxl
import pandas as pd
from datetime import datetime
import time
import logging
from io import StringIO
logging.basicConfig(filename='log.txt', encoding='utf-8', level=logging.DEBUG)

EMERGENCY = True
NOT_EMERGENCY = False
PATIENT_DISCHARGE_STATUS_CODES = {"Still a patient": 30, "Transferred to other inpatient hospital": 5, "Expired": 20}

# Code for uploading and processing file given by user
def upload_and_process_file():
    """
    Upload the user specified file (CSV only for now) and return a pandas dataframe. Currently only handles single file uploads.
    """

    # TODO Generalize this to different file types and separators

    columns_to_use = ["BENE_ID", "CLM_ID", "CLM_IP_ADMSN_TYPE_CD", "REV_CNTR", "CLM_ADMSN_DT", 
                      "NCH_BENE_DSCHRG_DT", "PTNT_DSCHRG_STUS_CD", "PRNCPAL_DGNS_CD", "HCPCS_CD", "Previous Emergency Dept Use (Past 6 Months)"]
    icd_cols = ["ICD_DGNS_CD" + str(i) for i in range(1, 26)]
    columns_to_use += icd_cols
    
    help = 'The file must have the following columms: "BENE_ID", "CLM_ID", "REV_CNTR", "CLM_ADMSN_DT", \
            "NCH_BENE_DSCHRG_DT", "PTNT_DSCHRG_STUS_CD", "PRNCPAL_DGNS_CD", "HCPCS_CD".'

    file = st.file_uploader("Upload medicare fee-for-service claim file:", accept_multiple_files=False, type=".csv", key="claims_upload", help=help)
    try_example = st.button("Try an example file", help="Source of file: https://data.cms.gov/sites/default/files/2023-04/67157de9-d962-4af0-bf0e-3578b3afec58/inpatient.csv")
    if try_example:
        # Use the example inpatient medicare fee-for-service claim file.
        df = pd.read_csv("inpatient78059.csv", sep="|", low_memory = False)
    elif file is not None:
        # Use the user-uploaded file.
        df = pd.read_csv(file, sep="|", low_memory = False)
    else:
        exit(3)

    # Filter the DataFrame based on available columns
    available_columns = df.columns
    columns_to_use = [col for col in columns_to_use if col in available_columns]
    df = df[columns_to_use]
    return df

# Calculate length of stay
def length_of_stay(df_row):
    """
    Calculate length of stay in number of days.
    """
    admsn_date, dschrg_date, dschrg_status = df_row["CLM_ADMSN_DT"], df_row["NCH_BENE_DSCHRG_DT"], df_row["PTNT_DSCHRG_STUS_CD"]
    admsn_date, dschrg_date = datetime.strptime(admsn_date, '%d-%b-%Y'), datetime.strptime(dschrg_date, '%d-%b-%Y')
    
    if dschrg_status == 30: # Patient is still a patient
        return
    elif dschrg_status == 20: # Patient died
        return
    elif dschrg_status == 5: # Patient transferred to different inpatient hospital
        return # We need the claims file from the different hospital and see how long the patient stayed there
    time_diff = dschrg_date - admsn_date
    return time_diff.days

# Based on row of Medicare claims data, figure out if the patient had an acute/emergent admission
def acuity_of_admission(df_row):
    docstring = """
    Input: Row of Medicare claims data 
    Output: Whether or not patient had an acute/emergent admission (i.e., via the ER)

    Algorithm here is based on https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5905698/. 
    """
    # print(df_row["REV_CNTR"])
    try:
        if df_row["CLM_IP_ADMSN_TYPE_CD"] in [1, 5]:
            return EMERGENCY
    except:
        # logging.info("Dataframe does not have CLM_IP_ADMSN_TYPE_CD column.")
        pass

    if 450 <= df_row["REV_CNTR"] <= 459 or df_row["REV_CNTR"] == 981:
        return EMERGENCY
    elif "99281" <= df_row["HCPCS_CD"] <= "99285" or df_row["HCPCS_CD"] == "99291":
        return EMERGENCY
    else:
        return NOT_EMERGENCY

# Functions for getting Charlson's comorbidity score (doesn't include age as a direct factor)

def get_charlson_comorbidity(icd_10_code):
    """
    Input: Patient's ICD 10 CM code
    Output: Patient's disease(s) based on code
    Notes:
    The coding is consistent with https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6684052/ (see supplementary materials). 
    The decmials are stripped away from the dict entries to be consistent with the medicare claim file format.
    """

    if type(icd_10_code) != str:
        return []
    
    # Dictionary specifying comorbidities and corresponding icd 10 codes.
    # Ranges are in tuples (start, end) where the range is [start, end)
    comorbidities = {
        # Diseases with 1 point on comorbidity index
        "Myocardial infarction": ["I21", "I22", "I252"],
        "Peripheral vascular disease": ["I70", "I71", "I731", "I738", "I739", "I771", "I790", "I791", "I798", "K551", "K558", "K559", "Z958", "Z959"], 
        "Cerebrovascular disease": ["G45", "G46", "H340", "H341", "H342", ("I60", "I69")], 
        "Diabetes without chronic complications": ["E080", "E081", "E086", "E088", "E089", 
                                                   "E090", "E091", "E096", "E098", "E099",
                                                   "E100", "E101", "E106", "E108", "E109",
                                                   "E110", "E111", "E116", "E118", "E119", 
                                                   "E130", "E131", "E136", "E138", "E139"],
        
        # Diseases with 2 pts on comorbidity index
        "Heart failure": ["I110", "I130", "I132", "I255", "I420", ("I425", "I43"), "I43", "I50", "P290"],
        "Chronic pulmonary disease": [("J40", "J48"), ("J60", "J68"), "J684", "J701", "J703"],
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
        "Dementia": [("F01", "F06"), "F061", "F068", "G132", "G138", "G30", ("G310", "G313"), "G914", "G94", "R4181", "R54"],

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
        
        # Diseases currently with 0 points on comorbidity index for LACE, but could change in future versions
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

def get_all_charlson_comorbidities(df_row):
    """
    Input <- row from inpatient medicare claims file.
    output <- list of patient's charlson's comorbidities
    """
    comorbidity_columns = ["PRNCPAL_DGNS_CD"] 
    comorbidity_columns += ["ICD_DGNS_CD" + str(i) for i in range(1, 26)]
    charlson_comorbidities = []
    for col in comorbidity_columns:
        try:
            code = df_row[col]
        except:
            # logging.info("Column" + str(col) + "doesn't exist in dataframe")
            # Log code doesn't exist
            continue
        comorbidity = get_charlson_comorbidity(code)
        charlson_comorbidities += list(comorbidity)
    charlson_comorbidities = set(charlson_comorbidities)
        
    priorities = [("Metastatic solid tumor", "Any malignancy"), 
                  ("Diabetes with chronic complications", "Diabetes without chronic complications"), 
                  ("Moderate or severe liver disease", "Mild liver disease"), 
                  ("AIDS", "HIV"), 
                  ("Renal disease (severe)", "Renal disease (mild or moderate)")]
    
    # if both high priority (i.e., severity) and low priority (less severe version) of the disease are listed, only keep the more severe (higher priority) disease version
    for high_priority, low_priority in priorities: 
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

# LACE Score calculation and interpretation

def calculate_lace_score(length_of_stay, acute_admission, charlson_index, ed_visits):
    """
    Algorithm to calculate LACE index score based on input variables
    """
    # Length of stay points
    if length_of_stay < 1:
        los_points = 0
    elif length_of_stay == 1:
        los_points = 1
    elif length_of_stay == 2:
        los_points = 2
    elif length_of_stay == 3:
        los_points = 3
    elif 4 <= length_of_stay <= 6:
        los_points = 4
    elif 7 <= length_of_stay <= 13:
        los_points = 5
    elif length_of_stay >= 14:
        los_points = 7

    # Acute/emergent admission points
    aa_points = 3 if acute_admission else 0

    # Charlson Comorbidity Index points
    
    if charlson_index <= 3:
        charlson_points = charlson_index
    else:
        charlson_points = 5

    # ED visits points
    ed_points = min(ed_visits, 4)

    # Calculates LACE index based on above points
    lace_score = los_points + aa_points + charlson_points + ed_points

    return lace_score

def interpret_lace_score(lace_score):
    if lace_score <= 4:
        return "LOW"
    elif 5 <= lace_score <= 9:
        return "INTERMEDIATE"
    else:
        return "HIGH"

def process_row(row):
    """
    Processes a row of a medicare claims file and outputs an entry consisting of that processed information
    """
    admsn_date, dschrg_date, dschrg_status = row["CLM_ADMSN_DT"], row["NCH_BENE_DSCHRG_DT"], row["PTNT_DSCHRG_STUS_CD"]
    admsn_date, dschrg_date = datetime.strptime(admsn_date, '%d-%b-%Y'), datetime.strptime(dschrg_date, '%d-%b-%Y')
    los = length_of_stay(row)
    acuity = acuity_of_admission(row)
    comorbidities = get_all_charlson_comorbidities(row)
    charlson_score = get_comorbidity_index_from_disease_list(comorbidities)
    emergency_dept_use = int(row["Previous Emergency Dept Use (Past 6 Months)"])
    lace_score = calculate_lace_score(los, acuity, charlson_score, emergency_dept_use)
    readmission_risk = interpret_lace_score(lace_score)
    entry = {
            "admission_date": admsn_date,
            "discharge_status": dschrg_status,
            "discharge_date": dschrg_date,
            "LACE_score": lace_score,
            "readmission_risk": readmission_risk,
            "los": los,
            "acuity": acuity,
            "comorbidities": comorbidities,
            "charlson_score": charlson_score,
            "emergency_dept_use": emergency_dept_use
            #TODO: Work ere
        }
    return entry

@st.cache_data
def convert_beneficiary_info_to_dataframe(beneficiaries_):
    """
    Inputs: beneficiaries_ <- contains the information about each patient, based on the claims file and the processing of it
    Outputs: df <- returns a dataframe containing the same information in a well-formatted manner
    
    """
    df = pd.DataFrame.from_dict(beneficiaries_, orient='index')
    df.reset_index(inplace=True)
    df.columns = ['Beneficiary ID', 'Admission Date', 'Discharge Status', 'Discharge Date', "LACE Score", "30-Day Readmission Risk", "Length of Stay (Days)", 
                  "Admission Is Acute", "Comorbidities", "Comorbidity Index", "Previous Emergency Dept Use (Past 6 Months)"]
    df = df[['Beneficiary ID', 'LACE Score', "30-Day Readmission Risk", "Length of Stay (Days)", "Admission Is Acute", "Comorbidity Index", 
             "Previous Emergency Dept Use (Past 6 Months)", "Comorbidities", "Admission Date", "Discharge Date", "Discharge Status"]]
    return df


def display_beneficiaries_dataframe(df):
    """
    Inputs: df <- contains information about each inpatient in claims file
    Behavior: displays df on streamlit with options to sort, etc.
    """
    # def highlight_rows(row):
    #     if s["30-Day Readmission Risk"] == "HIGH":
    #         return ['background-color: red']*len(row)
    #     elif s["30-Day Readmission Risk"] == "INTERMEDIATE":
    #         return ['background-color: yellow']*len(row)
    #     elif s["30-Day Readmission Risk"] == "LOW":
    #         return ['background-color: green']*len(row)

    st.markdown(
    "### LACE Score Table:\n"
    "- **Sorting:** You can sort the data by clicking on any column header.\n"
    "- **Downloading Data:** To download the data displayed in the table, "
    "hover your mouse over the table and click the download icon that appears "
    "at the upper right corner.\n"
    "- **Searching Data:** For a quick search within the table, hover your mouse "
    "over the table and use the magnifying glass icon that appears at the upper "
    "right corner.\n\n"
    "**Note:** The table below will display the LACE score for each patient along "
    "with associated risk levels and other relevant details. Ensure your CSV file "
    "contains the necessary columns for accurate score computation."
    )

    # st.dataframe(df.style.apply(highlight_rows, axis=1))
    st.dataframe(df)

@st.cache_data
def process_dataframe(df):
    nrows = len(df.axes[0])
    beneficiaries = dict()
    expired_beneficiaries = set()
    # Go row by row, process the data, and create a dictionary of beneficiaries with LACE scores and other important info
    for index, row in df.iterrows():
        bene_id = row["BENE_ID"]
        admsn_date, dschrg_date, dschrg_status = row["CLM_ADMSN_DT"], row["NCH_BENE_DSCHRG_DT"], row["PTNT_DSCHRG_STUS_CD"]
        admsn_date, dschrg_date = datetime.strptime(admsn_date, '%d-%b-%Y'), datetime.strptime(dschrg_date, '%d-%b-%Y')

        # If patient died or is still a patient, don't calculate LACE score yet. If patient died, don't add any claims with his BENE_ID to the beneficiaries dictionary.
        if dschrg_status == PATIENT_DISCHARGE_STATUS_CODES["Expired"]:
            expired_beneficiaries.add(bene_id)
        elif dschrg_status in [PATIENT_DISCHARGE_STATUS_CODES["Still a patient"], PATIENT_DISCHARGE_STATUS_CODES["Transferred to other inpatient hospital"]]:
            continue
        if bene_id in expired_beneficiaries:
            continue

        # Set up table of bene_ids and other info to lookup in diff files
        dschrg_status = int(row["PTNT_DSCHRG_STUS_CD"])
        if bene_id not in beneficiaries:
            if dschrg_status == PATIENT_DISCHARGE_STATUS_CODES["Expired"]:
                pass
            else:
                entry = process_row(row)
                beneficiaries[bene_id] = entry
        else: # Deals with the case where the beneficiary is already accounted for in the previous claim(s) or claim lines
            if dschrg_status == PATIENT_DISCHARGE_STATUS_CODES["Expired"]:
                del beneficiaries[bene_id]
            # This means that the current line/claim does not focus on the beneficiary's latest admission; so we ignore it.
            elif admsn_date < beneficiaries[bene_id]["admission_date"]: 
                pass
            elif admsn_date == beneficiaries[bene_id]["admission_date"]:
                try:
                    # Handle cases where one of them is blank (mostly done)
                    if dschrg_status == PATIENT_DISCHARGE_STATUS_CODES["Still a patient"] \
                                        or dschrg_date > beneficiaries["BENE_ID"]["discharge_date"]: 
                        entry = process_row(row)
                        entry["los"] = "Not applicable"
                        beneficiaries[bene_id] = entry
                    acuity = acuity_of_admission(row)
                    if acuity:
                        beneficiaries[bene_id]["acuity"] = True
                except Exception as e:
                    logging.warning(e)
            elif admsn_date > beneficiaries[bene_id]["admission_date"]:
               entry = process_row(row)
               beneficiaries[bene_id] = entry
        
    # Output patients LACE scores along with other pertinent information
    df_new = convert_beneficiary_info_to_dataframe(beneficiaries)
    return df_new

def convert_df_to_csv(df):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def main():
    # Initialize variables and process file
    initial_time = time.time()
    st.title("App for Calculating LACE Scores from Medicare Claims")
    st.markdown(
    "### Instructions:\n"
    "1. **Upload File:** To begin, upload your Medicare fee-for-service claim file by dragging "
    "and dropping it into the designated area or clicking the 'Browse files' button. Please note, "
    "the file must be in CSV format and not exceed 200MB.\n"
    "2. **Example File:** If you're new to the app or would like to see a demonstration, click "
    "'Try an example file' to use a pre-loaded dataset and view the LACE scores calculated by the app."
    )

    df = upload_and_process_file()

    progress= st.empty()
    progress.info("Calculating patients' LACE scores. Depending on the file size \
                   and internet connection, this might take up to 30+ seconds.")
    df_new = process_dataframe(df)

    # Display on Streamlit
    display_beneficiaries_dataframe(df_new)
    progress.empty()
    
    # Print out time the program took to run to console 
    # (for debugging and performance monitoring purposes)
    end_time = time.time()
    print(end_time - initial_time)

if __name__ == '__main__':
    main()
