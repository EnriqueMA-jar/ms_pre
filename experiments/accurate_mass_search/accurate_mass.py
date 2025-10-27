import pyopenms as oms
import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
import plotly.express as px
import os

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
    adduct_mode = detect_adduct_mode(adducts_path)
    ams_params.setValue("ionization_mode", adduct_mode)
    if adduct_mode == "positive":
        ams_params.setValue("positive_adducts", adducts_path)
        print("Positive adducts detected.")
    elif adduct_mode == "negative":
        ams_params.setValue("negative_adducts", adducts_path)
        print("Negative adducts detected.")
    ams_params.setValue("db:mapping", [db_mapping_path])
    ams_params.setValue("db:struct", [db_structure_path])
    ams.setParameters(ams_params)
    
    # Load consensusXML into ConsensusMap
    consensus_map = oms.ConsensusMap()
    oms.ConsensusXMLFile().load(consensus_path, consensus_map)
    mztab = oms.MzTab()
    # oms.MzTabFile().store(os.path.join(uploads_dir, f"{consensus_basename}_ids.tsv"), mztab)
    
    ams.init()
    # Pass ConsensusMap object instead of file path
    ams.run(consensus_map, mztab)
    consensus_basename = os.path.basename(consensus_path).rsplit(".", 1)[0]
    oms.MzTabFile().store(os.path.join(uploads_dir, f"{consensus_basename}_ids.tsv"), mztab)
    
    fig_id, id_file, id_filtered_file = plot_identifications(consensus_map, mztab, uploads_dir, consensus_basename)
    
   

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
    identifications_filtered_path = os.path.join(uploads_dir, f"{consensus_basename}_ids_with_identifications.tsv")
    csv_filtered.to_csv(csv_filtered_path, index=False)
    
    return csv_path, csv_filtered_path, identifications_filtered_path, fig_id

def detect_adduct_mode(adducts_path):
    with open(adducts_path, "rb") as f:
        print(f.readline())
    df = pd.read_csv(adducts_path, sep=";", header=None)
    charge_col = df[1].astype(str)
    if charge_col.str.endswith('-').sum() >  charge_col.str.endswith("+").sum():
        return "negative"
    else:
        return "positive"
    
def plot_identifications(consensus_map, mztab, uploads_dir, consensus_basename):
    print(f"Loaded ConsensusMap: {consensus_map.size()} features")
    
    # Get intensities and m/z values
    intensities = consensus_map.get_intensity_df()
    meta_data = consensus_map.get_metadata_df()[["RT", "mz", "quality"]]


    # Combine data into a single DataFrame
    cm_df = pd.concat([meta_data, intensities], axis=1)
    cm_df.reset_index(drop=True, inplace=True)
    
    id_df = cm_df.copy()
    id_df["identifications"] = pd.Series(["" for x in range(len(id_df.index))])
    
    try:
        # Extract small molecule section from mzTab using utf-8 encoding
        mztab_path = os.path.join(uploads_dir, f"{consensus_basename}_ids.tsv")
        temp_sm_file = "temp_sm_section.tsv"
        with open(temp_sm_file, "w", encoding="utf-8") as output, open(mztab_path, "r", encoding="utf-8", errors="ignore") as input_file:
            for line in input_file:
                if line.lstrip().startswith("SMH"):
                    output.write(line[4:])  # Header
                elif line.lstrip().startswith("SML"):
                    output.write(line[4:])  # Data lines
    
        ams_df = pd.read_csv(temp_sm_file, sep="\t", encoding="utf-8")
        os.remove(temp_sm_file)
    
        # print(f"Identifications loaded from mzTab (before filtering): {ams_df.shape}")
        
        # print("Ejemplo RT/mz ConsensusMap:", id_df[["RT", "mz"]].head(10))
        # print("Ejemplo RT/mz Identifications:", ams_df[["retention_time", "exp_mass_to_charge"]].head(10))
    
        # Filter rows where 'identifier' is 'null' or NaN
        if 'identifier' in ams_df.columns:
            ams_df = ams_df[
                (ams_df['identifier'] != 'null') & 
                (ams_df['identifier'].notna()) &
                (ams_df['identifier'] != '')
            ]
    
        # Filter 'description' also
        if 'description' in ams_df.columns:
            ams_df = ams_df[
                (ams_df['description'] != 'null') & 
                (ams_df['description'].notna()) &
                (ams_df['description'] != '')
            ]

        # print(f"Identifications after filtering nulls: {ams_df.shape}")
        # print(ams_df.head())
    
    except Exception as e:
        print(f"Error loading mzTab: {e}")
        ams_df = None

    
    
    if ams_df is not None and not ams_df.empty:
        for rt, mz, description in zip(
            ams_df["retention_time"],
            ams_df["exp_mass_to_charge"],
            ams_df["description"],
        ):
            indices = id_df.index[
                np.isclose(id_df["mz"], float(mz), atol=1e-05)
                & np.isclose(id_df["RT"], float(rt), atol=1e-05)
            ].tolist()
        
            for index in indices:
                if str(description) != "null" and pd.notna(description):
                    id_df.loc[index, "identifications"] += str(description) + ";"

    # Cleaning ; at the end
    id_df["identifications"] = [
        item[:-1] if ";" in item else "" for item in id_df["identifications"]
    ]
    
    id_df.to_csv("result.tsv", sep="\t", index=False)
    
    # Filter only features with identifications
    id_df_filtered = id_df[id_df["identifications"] != ""].copy()
    id_df_filtered.to_csv(os.path.join(uploads_dir, f"{consensus_basename}_ids_with_identifications.tsv"), sep="\t", index=False)
    # print(f"Resultado solo con identificaciones guardado en {consensus_basename}_ids_with_identifications.tsv: {id_df_filtered.shape}")
    # print(f"Features con identificaciones: {len(id_df_filtered)} de {len(id_df)} ({len(id_df_filtered)/len(id_df)*100:.2f}%)")

    # print(id_df.head())
    
    id_df_plot = id_df[id_df["identifications"] != ""].copy()

    fig = px.scatter(
        id_df_plot, 
        x="RT", 
        y="mz", 
        hover_name="identifications",
        title=f"Features with Identifications (n={len(id_df_plot)})"
    )
    fig.update_traces(marker=dict(size=8, opacity=0.7))
    # fig.show()
    
    fig.update_layout(
        # title={
        #     'text': "Features Map - FeatureXML",
        #     'x': 0.5,
        #     'xanchor': 'center',
        #     'font': {'size': 18, 'family': 'Arial'}
        # },
        # xaxis_title="Retention Time (RT)",
        # yaxis_title="m/z",
        width=1280,
        height=500,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            title="Files",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig, id_df, id_df_filtered