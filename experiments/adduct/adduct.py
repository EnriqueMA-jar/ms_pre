import pyopenms as oms
import pandas as pd
import os



def convert_adducts_csv_to_ams_tsv(input_csv, output_tsv):
            df = pd.read_csv(input_csv)
            df.drop_duplicates(subset=["adduct"], inplace=True)
            df = df.dropna(subset=["adduct", "charge"])
            df = df[df["adduct"].astype(str).str.strip() != ""]
            df = df[df["charge"] != 0]
            df = df[df["charge"] != "0"]
            print(df["adduct"].head(10))
            rows = []
            for _, row in df.iterrows():
                adduct = str(row.get("adduct"))
                if pd.isnull(adduct):
                    continue
                formula = adduct
                charge = row.get("charge", "")
                mass = row.get("mz", "")
                prob = "" 
                rows.append([adduct, formula, charge, mass, prob])
            ams_df = pd.DataFrame(rows, columns=["Name", "Formula", "Charge", "Mass", "Probability"])
            ams_df["Charge"] = ams_df["Charge"].astype(int)
            ams_df.to_csv(output_tsv, sep="\t", index=False, encoding="utf-8", lineterminator='\n')


# Get feature files
def get_adduct_files(file_paths, output_dir):
    output_files = []
    output_files2 = []
    output_files3 = []
    for file in file_paths: 
        # Create a FeatureMap and load the featureXML file
        feature_map = oms.FeatureMap()
        oms.FeatureXMLFile().load(file, feature_map)
        
        # Initialize MetaboliteFeatureDeconvolution
        mfd = oms.MetaboliteFeatureDeconvolution()
        
        # Set parameters for adduct detection
        params = mfd.getDefaults()
        
        # Set adducts to search for
        params.setValue("potential_adducts", ["H:+:0.6", "Na:+:0.4", "H-2O-1:0:0.2"])
        
        # Set charge range and retention time differences
        params.setValue("charge_min", 1, "Minimal possible charge")
        params.setValue("charge_max", 3, "Maximal possible charge")
        params.setValue("charge_span_max", 3)
        params.setValue("retention_max_diff", 3.0)
        params.setValue("retention_max_diff_local", 3.0)

        # Set updated parameters
        mfd.setParameters(params)
        
        # Create an empty FeatureMap to store results
        feature_map_MFD = oms.FeatureMap()
        groups = oms.ConsensusMap()
        edges = oms.ConsensusMap()
        
        # Run the adduct detection
        mfd.compute(feature_map, feature_map_MFD, groups, edges)
        
        # Export the data to a pandas DataFrame
        df = feature_map_MFD.get_df(export_peptide_identifications=False)
        df["adduct"] = [f.getMetaValue("dc_charge_adducts") if f.metaValueExists("dc_charge_adducts") else None for f in feature_map_MFD]
        
        
        output_file = f"{output_dir}/{os.path.basename(file).replace('.featureXML', '_adducts.csv')}"
        output_file2 = f"{output_dir}/{os.path.basename(file).replace('.featureXML', '_adducts.featureXML')}"
        output_file3 = f"{output_dir}/{os.path.basename(file).replace('.featureXML', '_adducts_db.tsv')}"
        # Save the DataFrame to a CSV file
        df.to_csv(output_file, index=False)
        output_files.append(output_file)
        
        # Prepare and save the adduct database file
        
        df2 = df.filter(items=['adduct', 'charge']).copy()
        df2 = df2.dropna(subset=['adduct'])
        
        if df2.empty:
            continue
        else:
            df2 = df2.drop_duplicates()
            adduct_rows = []
            for _, row in df2.iterrows():
                adduct = str(row['adduct'])
                charge = int(row['charge'])
                adduct_clean = adduct.replace('+', ' ').replace('-', ' ')
                adduct_clean = ' '.join(adduct_clean.split())
                if charge > 0:
                    # adduct_formatted = f"M+{adduct_clean.replace(' ', '+')};{charge}+"
                    row['adduct'] = f"M+{adduct_clean.replace(' ', '+')}"
                    row['charge'] = f"{charge}+"
                elif charge < 0:
                    # adduct_formatted = f"M-{adduct_clean.replace(' ', '-')};{abs(charge)}-"
                    row['adduct'] = f"M-{adduct_clean.replace(' ', '-')}"
                    row['charge'] = f"{abs(charge)}-"
                else:
                    continue
                adduct_rows.append([row['adduct'], row['charge']])
            df_out = pd.DataFrame(adduct_rows)
            print(df_out.head(10))
            df_out.to_csv(output_file3, index=False, header=False, sep=";")

        # Converting the csv to the required tsv format Name, Formula, Charge, Mass, Probability
            
        # convert_adducts_csv_to_ams_tsv(output_file, output_file3)

        output_files3.append(output_file3)
        
        oms.FeatureXMLFile().store(output_file2, feature_map_MFD)
        output_files2.append(output_file2)
        
        
        
    return output_files, output_files2, output_files3
        
    