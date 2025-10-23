import pyopenms as oms
import pandas as pd
import os

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
        
        df2 = df.filter(items=['adduct', 'charge'])
        df2["charge"] = df2["charge"].astype(str) + "+"
        df2 = df2.drop_duplicates()
        

        df2.to_csv(output_file3, index=False, header=False, sep=";")
        output_files3.append(output_file3)
        
        oms.FeatureXMLFile().store(output_file2, feature_map_MFD)
        output_files2.append(output_file2)
        
        
        
    return output_files, output_files2, output_files3
        
    