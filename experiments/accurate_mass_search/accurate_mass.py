import os
import pyopenms as oms
import pandas as pd

def remove_useless_userparams(featurexml_path):
    """
    Remove UserParam tags from the FeatureMap level in a featureXML file.
    This prevents OpenMS errors when loading as ConsensusXML.
    """
    try:
        fm = oms.FeatureMap()
        oms.FeatureXMLFile().load(featurexml_path, fm)
        fm.clearMetaInfo()
        for f in fm:
            f.clearMetaInfo()
        oms.FeatureXMLFile().store(featurexml_path, fm)
    except Exception as e:
        print(f"[WARN] Could not clean UserParams from {featurexml_path}: {e}")

def load_files(consensus_path, db_mapping_path, db_structure_path, adducts_path, uploads_dir):
    # Remove UserParams if the input is actually a featureXML (user error)
    if consensus_path.endswith(".featureXML"):
        remove_useless_userparams(consensus_path)
    ams = oms.AccurateMassSearchEngine()
    ams_params = ams.getParameters()
    ams_params.setValue("ionization_mode", "positive")
    ams_params.setValue(
        "positive_adducts", adducts_path
    )
    ams_params.setValue("db:mapping", [db_mapping_path])
    ams_params.setValue("db:struct", [db_structure_path])
    ams.setParameters(ams_params)
    
    # Load consensusXML into ConsensusMap
    consensus_map = oms.ConsensusMap()
    oms.ConsensusXMLFile().load(consensus_path, consensus_map)
    
    mztab = oms.MzTab()
    ams.init()
    # Pass ConsensusMap object instead of file path
    ams.run(consensus_map, mztab)
    consensus_basename = os.path.basename(consensus_path).rsplit(".", 1)[0]
    oms.MzTabFile().store(os.path.join(uploads_dir, f"{consensus_basename}_ids.tsv"), mztab)

    with open(os.path.join(uploads_dir, f"{consensus_basename}_ids_smsection.tsv"), "w") as output, open(os.path.join(uploads_dir, f"{consensus_basename}_ids.tsv"), "r") as input:
        for line in input:
            if line.startswith("SM"):
                output.write(line[4:])

    ams_df = pd.read_csv(os.path.join(uploads_dir, f"{consensus_basename}_ids_smsection.tsv"), sep="\t")

    # Removing temporary files
    # os.remove(os.path.join(uploads_dir, f"{consensus_basename}_ids.tsv"))
    # os.remove(os.path.join(uploads_dir, f"{consensus_basename}_ids_smsection.tsv"))

    csv = ams_df.to_csv(index=False)
    csv_path = os.path.join(uploads_dir, f"{consensus_basename}_ids_smsection.csv")

    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv)

    csv_filtered = ams_df[ams_df['identifier'].notnull()]
    csv_filtered_path = os.path.join(uploads_dir, f"{consensus_basename}_ids_smsection_filtered.csv")
    csv_filtered.to_csv(csv_filtered_path, index=False)
    
    

    return csv_path, csv_filtered_path