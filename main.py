import streamlit as st

def calculate_charlson_index():
    # Tooltips for below functions
    previous_myocardial_infarction_def = "Any previous definite or probable myocardial infarction"
    cerebrovascular_disease_def = "Any previous stroke or transient ischemic attack (TIA)"
    peripheral_vascular_disease_def = "Intermittent claudication, previous surgery or stenting, gangrene or acute ischemia, untreated abdominal or thoracic aortic aneurysm"
    diabetes_without_complications_def = "No retinopathy, nephropathy, or neuropathy"
    congestive_heart_failure_def = "Any patient with symptomatic CHF whose symptoms have responded to appropriate medications"
    
    diabetes_with_end_organ_damage_def = "Diabetes with retinopathy, nephropathy, or neuropathy"
    chronic_pulmonary_disease_def = "?"
    mild_liver_or_renal_disease_def = "Cirrhosis but no portal hypertension (i.e., no varices, no ascites) OR chronic hepatitis; Chronic renal disease"
    cancer_def = "Solid tumors must have been treated within the last 5 years; includes chronic lymphocytic leukemia (CLL), polycythemia vera (PV), and other lymphomas/leukemias"
    
    dementia_def = "?"
    connective_tissue_disease_def = "Systemic lupus erythematosus (SLE), polymyositis, mixed connective tissue disease, moderate to severe rheumatoid arthritis, and polymyalgia rheumatica"

    aids_def = "AIDS-defining opportunistic infection or CD4 < 200"
    moderate_or_severe_liver_or_renal_disease_def = "Cirrhosis with portal hypertension (e.g., ascites or variceal bleeding); End-Stage Renal Disease, Hemodialysis, or Peritoneal Dialysis"
    metastatic_solid_tumor_def = "Any metastatic solid tumor"


    # UI for the functions
    previous_myocardial_infarction = st.checkbox("Previous myocardial infarction", help=previous_myocardial_infarction_def)
    cerebrovascular_disease = st.checkbox("Cerebrovascular disease", help=cerebrovascular_disease_def)
    peripheral_vascular_disease = st.checkbox("Peripheral vascular disease", help=peripheral_vascular_disease_def)
    diabetes_without_complications = st.checkbox("Diabetes without complications", help=diabetes_without_complications_def)
    congestive_heart_failure = st.checkbox("Congestive Heart Failure", help=congestive_heart_failure_def)
    

    diabetes_with_end_organ_damage = st.checkbox("Diabetes with end organ damage", help=diabetes_with_end_organ_damage_def)
    chronic_pulmonary_disease = st.checkbox("Chronic Pulmonary Disease")
    mild_liver_or_renal_disease = st.checkbox("Mild liver or renal disease", help=mild_liver_or_renal_disease_def)
    cancer = st.checkbox("Any tumor (including lymphoma or leukemia)", help=cancer_def)
    
    dementia = st.checkbox("Dementia")
    connective_tissue_disease = st.checkbox("Connective tissue disease", help=connective_tissue_disease_def)
    

    aids = st.checkbox("AIDS", help=aids_def)
    moderate_or_severe_liver_or_renal_disease = st.checkbox("Moderate or severe liver or renal disease", help=moderate_or_severe_liver_or_renal_disease_def)
    
    metastatic_solid_tumor = st.checkbox("Metastatic solid tumor", help=metastatic_solid_tumor_def)
    
    # Calculate Charlson's Index given input
    score = 0
    score += (previous_myocardial_infarction + cerebrovascular_disease + peripheral_vascular_disease
              + diabetes_without_complications + congestive_heart_failure)
    score += 2*(diabetes_with_end_organ_damage + chronic_pulmonary_disease + mild_liver_or_renal_disease + cancer)
    score += 3*(dementia + connective_tissue_disease)
    score += 4*(aids + moderate_or_severe_liver_or_renal_disease)
    score += 6*metastatic_solid_tumor

    st.write("**Based on the above information, the patient's Charlson's Comorbidity score is " + str(score) + ".**\n")

    return score

def calculate_lace_score(length_of_stay, acute_admission, charlson_index, ed_visits):
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

    # Total LACE score
    lace_score = los_points + aa_points + charlson_points + ed_points
    return lace_score

# Streamlit app
st.title("LACE Index Score Calculator")
st.write("Calculate a patient's LACE score based on Length of stay, Acuity of admission, \
         Comorbidities, and Emergency department visits within the past 6 months. More details of the algorithm \
         can be found at [https://txhca.org/app/uploads/2015/08/Aug.-2015-LACE-Tool.pdf](https://txhca.org/app/uploads/2015/08/Aug.-2015-LACE-Tool.pdf).")
# User inputs
length_of_stay_help = "Length of stay (including day of admission and discharge)"
st.subheader("Step 1: Length of Stay", help=length_of_stay_help)
length_of_stay = st.number_input("Length of Stay (days)", min_value=0)

acuity_of_admission_help = "Was the patient admitted to the hospital via the emergency department?"
st.subheader("Step 2: Acuity of Admission", help = acuity_of_admission_help)
acute_admission = st.checkbox("Acute/Emergency Admission", key=0)

st.subheader("Step 3: Comorbidities")
charlson_index = calculate_charlson_index()

ER_visits_help = "How many times has the patient visited an emergency department prior to admission \
    (not including the emergency department visit immediately preceding the current admission)"
st.subheader("Step 4: Emergency department visits", help = ER_visits_help)
ed_visits = st.number_input("Number of emergency department visits in the last 6 months", min_value=0)

if st.button("Calculate LACE Score"):
    lace_score = calculate_lace_score(length_of_stay, acute_admission, charlson_index, ed_visits)
    st.subheader(f"The patient's LACE index score is: {lace_score}")
    if lace_score < 5:
        st.text("###Based on the LACE score, the patient is at low risk for hospital readmission.")
    elif 5 <= lace_score <= 9:
        st.text("###Based on the LACE score, the patient is at moderate risk for hospital readmission.")
    elif lace_score >= 10:
        st.text("###Based on the LACE score, teh patient is at high risk for hospital readmission.")
