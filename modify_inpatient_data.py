import pandas as pd
import numpy as np

def add_ER_visits():
    df = pd.read_csv("inpatient.csv", sep = "|", low_memory = False)
    nrows = df.shape[0]

    lambda_approx = 1.8
    random_visits = np.random.poisson(lambda_approx, nrows)
    df["Previous Emergency Dept Use (Past 6 Months)"] = random_visits

    df.to_csv("inpatient.csv", sep = "|", index=False)

def backup_inpatient_file():
    df = pd.read_csv("inpatient.csv", sep = "|", low_memory = False)
    df.to_csv("inpatient_copy.csv", sep = "|", index=False)
def test_backup_inpatient_file():
    # Load the CSV files into DataFrames
    df_inpatient_new = pd.read_csv('inpatient.csv', sep = "|")
    df_inpatient_copy = pd.read_csv('inpatient_copy.csv', sep = "|")

    # Performing a column-wise comparison to see the differences for each column
    # This will check for each column if any values are different
    column_diff_new = {}
    for column in df_inpatient_new.columns:
        # Check if any value in the column is different
        is_different = not df_inpatient_new[column].equals(df_inpatient_copy[column])
        column_diff_new[column] = is_different

    # Displaying the columns that have differences
    columns_with_diff_new = {col: diff for col, diff in column_diff_new.items() if diff}

    return columns_with_diff_new


def main():
    add_ER_visits()

if __name__ == "__main__":
    main()
