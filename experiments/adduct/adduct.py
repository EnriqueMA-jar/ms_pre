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


def process_adducts(file, output_dir, mode="positive"):
    """
    Process adducts for a single file.
    
    Args:
        file: Path to the featureXML file
        output_dir: Directory to save output files
        mode: "positive" or "negative" for the type of adducts to detect
    
    Returns:
        Tuple of (csv_file, featureXML_file, db_file) paths
    """
    # Create a FeatureMap and load the featureXML file
    feature_map = oms.FeatureMap()
    oms.FeatureXMLFile().load(file, feature_map)
    
    # Initialize MetaboliteFeatureDeconvolution
    mfd = oms.MetaboliteFeatureDeconvolution()
    
    # Set parameters for adduct detection
    params = mfd.getDefaults()
    
    # Set adducts based on mode (positive or negative)
    if mode == "positive":
        params.setValue("potential_adducts", ["H:+:0.6", "Na:+:0.4", "H-2O-1:0:0.2"])
        suffix = "_adducts_pos"
    else:  # negative
        params.setValue("potential_adducts", ["H-1:-:0.6", "Cl-1:-:0.3", "CH2O2:-:0.1"])
        suffix = "_adducts_neg"
    
    # Set charge range and retention time differences
    params.setValue("charge_min", 1, "Minimal possible charge")
    params.setValue("charge_max", 3, "Maximal possible charge")
    params.setValue("charge_span_max", 3)
    params.setValue("retention_max_diff", 3.0)
    params.setValue("retention_max_diff_local", 3.0)

    # Set updated parameters
    adducts = ["H-1:-:0.6", "Cl-1:-:0.4", "CH2O2:0:0.2"]
    suma_cargados = sum(float(a.split(":")[2]) for a in adducts if a.split(":")[1] != "0")
    print("Suma de probabilidades cargados:", suma_cargados)
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
    
    # Define output file paths
    base_name = os.path.basename(file).replace('.featureXML', '')
    output_file = f"{output_dir}/{base_name}{suffix}.csv"
    output_file2 = f"{output_dir}/{base_name}{suffix}.featureXML"
    output_file3 = f"{output_dir}/{base_name}{suffix}_db.tsv"
    
    # Save the DataFrame to a CSV file
    df.to_csv(output_file, index=False)
    
    # Save the featureXML file
    oms.FeatureXMLFile().store(output_file2, feature_map_MFD)
    
    # Prepare and save the adduct database file
    df2 = df.filter(items=['adduct', 'charge']).copy()
    df2 = df2.dropna(subset=['adduct'])
    
    if not df2.empty:
        df2 = df2.drop_duplicates()
        adduct_rows = []
        for _, row in df2.iterrows():
            adduct = str(row['adduct'])
            charge = int(row['charge'])
            adduct_clean = adduct.replace('+', ' ').replace('-', ' ')
            adduct_clean = ' '.join(adduct_clean.split())
            if charge > 0:
                row['adduct'] = f"M+{adduct_clean.replace(' ', '+')}"
                row['charge'] = f"{charge}+"
            elif charge < 0:
                row['adduct'] = f"M-{adduct_clean.replace(' ', '-')}"
                row['charge'] = f"{abs(charge)}-"
            else:
                continue
            adduct_rows.append([row['adduct'], row['charge']])
        df_out = pd.DataFrame(adduct_rows)
        print(f"{mode.capitalize()} adducts:")
        print(df_out.head(10))
        df_out.to_csv(output_file3, index=False, header=False, sep=";")
    
    return output_file, output_file2, output_file3


# Get feature files
def get_adduct_files(file_paths, output_dir, modes=None):
    """
    Process adduct detection for multiple files.
    
    Args:
        file_paths: List of paths to featureXML files
        output_dir: Directory to save output files
        modes: List of modes to process. Options: ["positive", "negative"] or ["positive"] or ["negative"]
               Default is ["positive", "negative"] (both)
    
    Returns:
        Dictionary with keys 'positive' and/or 'negative', each containing:
        - output_files: list of CSV files
        - output_files2: list of featureXML files
        - output_files3: list of db.tsv files
    """
    if modes is None:
        modes = ["positive", "negative"]
    
    results = {}
    
    for mode in modes:
        output_files = []
        output_files2 = []
        output_files3 = []
        
        for file in file_paths:
            csv_file, feature_file, db_file = process_adducts(file, output_dir, mode)
            output_files.append(csv_file)
            output_files2.append(feature_file)
            output_files3.append(db_file)
        
        results[mode] = {
            'csv_files': output_files,
            'featurexml_files': output_files2,
            'db_files': output_files3
        }
    
    return results


# Mantener compatibilidad con código existente
def get_adduct_files_positive(file_paths, output_dir):
    """Process only positive adducts (legacy function for backward compatibility)"""
    results = get_adduct_files(file_paths, output_dir, modes=["positive"])
    return (
        results["positive"]['csv_files'],
        results["positive"]['featurexml_files'],
        results["positive"]['db_files']
    )


def get_adduct_files_negative(file_paths, output_dir):
    """Process only negative adducts"""
    results = get_adduct_files(file_paths, output_dir, modes=["negative"])
    return (
        results["negative"]['csv_files'],
        results["negative"]['featurexml_files'],
        results["negative"]['db_files']
    )