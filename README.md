# LACE_model

The LACE Index Score Calculator is a Streamlit web application designed to assess the risk of post-discharge readmission or death within 30 days for patients who have been hospitalized. The calculator implements the LACE index scoring system, which takes into account the Length of stay (L), Acuity of admission (A), Comorbidities (C), and Emergency department visits (E).

## Features

- **LACE Score Calculation**: Utilizes patient data to compute a risk score based on the LACE index scoring system.
- **Medicare Claims Data Processing**: Analyzes claims data to automatically calculate LACE scores for multiple patients.

## How the Application Works

The application offers two methods for calculating the LACE score:

### Manual Input

1. **Length of Stay (Step 1)**: Input the total hospital stay days to get the corresponding LACE score.
2. **Acuity of Admission (Step 2)**: Indicate acute admission through the emergency department to add to the LACE score.
3. **Comorbidities (Step 3)**: Calculate the Charlson Comorbidity Index based on the patient's medical history.
4. **Emergency Department Visits (Step 4)**: Enter the number of emergency department visits to finalize the individual LACE score components.

### Automated Calculation from Claims Data

1. **Upload Claims Data**: The user uploads a Medicare claims data file in CSV format. The application is built to handle the specific structure of Medicare claims data for seamless processing.
2. **Data Processing**: The application parses the uploaded file, automatically identifying and calculating each component of the LACE score.
3. **LACE Score Computation**: After processing the data, the application computes the LACE score for each patient entry in the claims data.
4. **Results Presentation**: The calculated LACE scores, along with the associated risk level, are displayed in a sortable and searchable table, providing a comprehensive overview of all patients included in the claims data.
5. **Data Export**: Users have the option to download the resulting data, including calculated LACE scores, for further analysis or reporting.

## User Guide

- **Calculating LACE Score Manually**: Follow the step-by-step prompts to enter patient details and calculate the LACE score.
- **Using Medicare Claims Data**: Upload a CSV file of the claims data and let the application process it to generate LACE scores for multiple patients at once.

## Conclusion

The LACE Index Score Calculator provides healthcare professionals with a quick and user-friendly tool to aid in the evaluation of patients at the time of discharge planning. It assists in identifying those at higher risk who may benefit from more intensive post-discharge care to prevent adverse outcomes.
