import unittest
from process_claims import acuity_of_admission, length_of_stay, get_charlson_comorbidity, get_all_charlson_comorbidities, get_comorbidities_score
import pandas as pd
from datetime import datetime
# 3 h
class TestHealthDataProcessing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass
        # This method can be used to set up any test data or state that's shared across tests
    def setUp(self):
        # This method is called before each test
        # Here you can set up test data
        self.sample_row = {
            "CLM_IP_ADMSN_TYPE_CD": 1,
            "REV_CNTR": 450,
            "CLM_ADMSN_DT": "01-Jan-2020",
            "NCH_BENE_DSCHRG_DT": "10-Jan-2020",
            "PTNT_DSCHRG_STUS_CD": 30,
            "ICD_DGNS_CD1": "I214"
            # Add other necessary fields for testing
        }
        self.df_row = pd.Series(self.sample_row)

        self.sample_row2 = {
            "CLM_IP_ADMSN_TYPE_CD": 1,
            "REV_CNTR": 450,
            "CLM_ADMSN_DT": "01-Jan-2020",
            "NCH_BENE_DSCHRG_DT": "10-Jan-2020",
            "PTNT_DSCHRG_STUS_CD": 30,
            "PRNCPAL_DGNS_CD": "I214",
            "ICD_DGNS_CD1": "I2145", # Myocardial infarction
            "ICD_DGNS_CD2": "G45346", # Cerebrovascular disease
            "ICD_DGNS_CD25": "I71642", # Peripheral vascular disease
            "ICD_DGNS_CD4": "#53"
            # Add other necessary fields for testing
        }
        self.df_row2 = pd.Series(self.sample_row2)

        # Test subset of diseases (other diseasaes follow similar logic)

        # BUG CAUGHT: A code can code for 2 diseases
        self.test_codes = {
        "Myocardial infarction": ["I214", "I21A", "I225", "I252"],
        "Heart failure": ["I1109", "I130", "I132A", "I2550", "I4201", 
                            "I425", "I426", "14299", "I425",  "I50190", "P2902"],
        "Peripheral vascular disease": ["I704", "I71", "I7312", "I738A", "I739445", 
                                        "I77192", "I79059", "I79100", "I798001", 
                                        "K5514", "K5584", "K5596", "Z9584", "Z9593"],
        "Cerebrovascular disease": ["G45346", "G4680", "H340357", "H3414", "H3420", 
                                    "I60", "I67", "I68999"],
        "Diabetes without chronic complications": ["E080", "E081", "E086", "E088", "E089", 
            "E090", "E091", "E096", "E098", "E099",
            "E100", "E101", "E106", "E108", "E109",
            "E110", "E111", "E116", "E118", "E119",
            "E130", "E131", "E136", "E138", "E139"],

        # Diseases with 2 pts on comorbidity index
        "Heart failure": ["I110", "I255", "I420", "I425", "I426", "I4299", "I43", "I50", "P290"],
        "Chronic pulmonary disease": ["J40", "J47999", "J60", "J6799", "J684", "J701", "J703"], # Checked
        "Mild liver disease": ["B18", "K700", "K702", "K7033", "K70.9", "K713", "K7134", "K715999", "K717", "K73", "K74", "K760", "K762", "K76499", "K768", "K769", "Z944"],
        "Diabetes with chronic complications": ["E082", "E083", "E084", "E085", 
                                                "E092", "E093", "E094", "E095", 
                                                "E102", "E103", "E104", "E105", 
                                                "E112", "E113", "E114", "E115", 
                                                "E132", "E133", "E134", "E135"],
        "Renal disease (mild or moderate)": ["I129", "I1310", "N03", "N05", "N181", "N184999", "N189", "Z940"],
        "Any malignancy": ["C0", "C10", "C20", "C30", "C40", "C475656", "C5A6", "C6945", "C753", "C979999"],
        
        # Diseases with 3 pts on comorbidity index.
        "Connective tissue disease": ["M30", "M3699"], #TODO
        "Dementia": ["F01", "F059", "F061", "F068", "G132", "G138", "G30", "G310", "G31299", "G914", "G94", "R4181"], # Didn't include R54 as it's not specific to dementia
        
        # Diseases with 4+ points on comorbidity index.
        "Renal disease (severe)": ["I120", "I1311", "N185", "N186", "N19", "N250", "Z49", "Z992"],
        "Moderate or severe liver disease": ["I850", "I864", "K704", "K711", "K721", "K729", "K765", "K766", "K767"],
        # "AIDS": ["A021"], 
        "Metastatic solid tumor": ["C771", "C7B3", "C809"],
        
        # Diseases currently with 0 points on comorbidity index for LACE
        # but could change in future versions
        # "Rheumatic disease": ["M05", "M06", "M315", ("M32", "M35"), "M351", "M353", "M360"],
        # "Peptic ulcer disease": [("K25", "K29")],
        # "Hemiplegia or paraplegia": ["G041", "G114", "G800", "G801", "G802", "G81", "G82", "G83"],
        "HIV": ["B20"]                 
                                                           }
        

    def test_acuity_of_admission(self):
    # Test for emergency case
        self.assertTrue(acuity_of_admission(self.df_row))

    # Test for non-emergency case
        self.df_row["CLM_IP_ADMSN_TYPE_CD"] = 2 
        self.df_row["REV_CNTR"] = 100 # Change to a non-emergency code
        self.assertFalse(acuity_of_admission(self.df_row))

    def test_get_charlson_comorbidity(self):
        # Test with a specific ICD code
        for comorbidity, codes in self.test_codes.items():
            results = list()
            for code in codes:
                lst = get_charlson_comorbidity(code)
                results += lst
                if lst != [comorbidity]:
                    print(code, lst, comorbidity, "\n")
                    self.assertTrue(False)
            results = set(results)
            if len(results) > 1 or comorbidity not in results:
                print(comorbidity, results, "\n")
                self.assertTrue(False)

        # Test with an invalid ICD code
        result = get_charlson_comorbidity("XYZ")
        self.assertEqual(result, [])

    def test_get_all_charlson_comorbidities(self):
        self.assertTrue(sorted(get_all_charlson_comorbidities(self.df_row2)) == ["Cerebrovascular disease", "Myocardial infarction", "Peripheral vascular disease"])
    def test_get_comorbidities_score(self):
        self.assertTrue(get_comorbidities_score(self.df_row2) == 3)
if __name__ == '__main__':
    unittest.main()

