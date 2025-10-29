import pandas as pd
import pyopenms as oms
import os

def get_consensus_matrix(feature_file_paths, output_dir, empty_idmxl):
    
    feature_maps = []
    file_names = [os.path.basename(f) for f in feature_file_paths]

    matrix_name = "".join([os.path.splitext(name)[0] for name in file_names]).replace("_savgol","").replace("_centroided", "").replace("_Metabolomics","").replace("_Proteomics","").replace("_features","").replace("_aligned","").replace("_features","").replace("aligned_","").replace("-","").replace("_adducts","")

    # Cargar los FeatureMaps
    for feature_file in feature_file_paths:
        file_path = feature_file
        if os.path.exists(file_path):
            feature_map = oms.FeatureMap()
            oms.FeatureXMLFile().load(file_path, feature_map)
            feature_maps.append(feature_map)
            print(f"  - Loaded: {feature_file}")
        else:
            print(f"  - Error: {feature_file} not found, skipping...")

    # Cargar los archivos mzML (asumiendo que están en el mismo directorio y tienen nombres relacionados)
    mzml_files = []
    for name in file_names:
        # Busca archivos mzML con el mismo nombre base
        base = name.replace(".featureXML","")
        possible_mzml = os.path.join(output_dir, base + ".mzML")
        if os.path.exists(possible_mzml):
            mzml_files.append(possible_mzml)

    # Mapear identificaciones (IDMapper)
    feature_maps_mapped = []
    use_centroid_rt = False
    use_centroid_mz = True
    mapper = oms.IDMapper()
    for file in mzml_files:
        exp = oms.MSExperiment()
        oms.MzMLFile().load(file, exp)
        for i, feature_map in enumerate(feature_maps):
            # Verifica que el metadato coincida
            if feature_map.getMetaValue("spectra_data")[0].decode() == exp.getMetaValue("mzML_path"):
                peptide_ids = []
                protein_ids = []
                
                
                # Prepare peptide and protein identification lists
                # Ensure there's an empty idXML available for the mapper (OpenMS requires an idXML file)
                try:
                    if not empty_idmxl:
                        empty_idmxl = os.path.join(output_dir, "empty.idXML")
                    if not os.path.exists(empty_idmxl):
                        # print(f"Creating empty idXML at: {empty_idmxl}")
                        oms.IdXMLFile().store(empty_idmxl, protein_ids, peptide_ids)
                    else:
                        # load any existing identifications (likely empty)
                        oms.IdXMLFile().load(empty_idmxl, protein_ids, peptide_ids)
                except Exception as e:
                    print(f"Warning: could not create/load empty idXML '{empty_idmxl}': {e}")

                # Annotate features with peptide identifications mapped from spectra
                try:
                    mapper.annotate(
                        feature_map,
                        peptide_ids,
                        protein_ids,
                        use_centroid_rt,
                        use_centroid_mz,
                        exp,
                    )
                except Exception as e:
                    print(f"Error during IDMapper.annotate: {e}")

                # Optionally store the mapped identifications to an idXML per feature file for debugging
                try:
                    mapped_idxml_path = os.path.join(
                        output_dir,
                        os.path.splitext(os.path.basename(feature_file))[0] + ".mapped.idXML",
                    )
                    oms.IdXMLFile().store(mapped_idxml_path, protein_ids, peptide_ids)
                    print(f"Stored mapped idXML: {mapped_idxml_path}")
                except Exception as e:
                    print(f"Could not store mapped idXML: {e}")

                # Iterate features if needed (original code had a block here)
                for feature in feature_map:
                    pass
                
                
                fm_new = oms.FeatureMap(feature_map)
                fm_new.clear(False)
                # set unique identifiers to protein and peptide identifications
                prot_ids = []
                if len(feature_map.getProteinIdentifications()) > 0:
                    prot_id = feature_map.getProteinIdentifications()[0]
                    prot_id.setIdentifier(f"Identifier_{i}")
                    prot_ids.append(prot_id)
                fm_new.setProteinIdentifications(prot_ids)
                for feature in feature_map:
                    pep_ids = []
                    for pep_id in feature.getPeptideIdentifications():
                        pep_id.setIdentifier(f"Identifier_{i}")
                        pep_ids.append(pep_id)
                    feature.setPeptideIdentifications(pep_ids)
                    fm_new.push_back(feature)
                feature_maps_mapped.append(fm_new)
    if feature_maps_mapped:
        feature_maps = feature_maps_mapped

    feature_grouper = oms.FeatureGroupingAlgorithmKD()
    consensus_map = oms.ConsensusMap()
    file_descriptions = consensus_map.getColumnHeaders()

    for i, feature_map in enumerate(feature_maps):
        file_description = file_descriptions.get(i, oms.ColumnHeader())
        file_description.filename = os.path.basename(
            feature_map.getMetaValue("spectra_data")[0].decode()
        )
        file_description.size = feature_map.size()
        file_descriptions[i] =  file_description

    consensus_map.setColumnHeaders(file_descriptions)
    feature_grouper.group(feature_maps, consensus_map)
    consensus_map.setUniqueIds()

    output_path = os.path.join(output_dir, f"{matrix_name}.consensusXML")
    oms.ConsensusXMLFile().store(output_path, consensus_map)
    print(f"\nConsensus matrix saved to: {output_path}")
    
    oms.ConsensusXMLFile().load(output_path, consensus_map)
    
    column_headers = consensus_map.getColumnHeaders()
    print("\nColumn Headers in Consensus Map:")
    sorted_columns = sorted(column_headers.items(), key=lambda x: x[0])
    filenames = [os.path.basename(header.filename) for idx, header in sorted_columns] 

    # Construir el DataFrame
    rows = []
    print(f"Total consensus features: {consensus_map.size()}")
    for cf in consensus_map:
        row = {
            'rt': cf.getRT(),
            'mz': cf.getMZ(),
            'intensity': cf.getIntensity()
        }
        # Inicializar intensidades con NaN
        for filename in filenames:
            row[filename] = float('nan')
        # Llenar intensidades de cada archivo
        for fh in cf.getFeatureList():
            map_idx = fh.getMapIndex()
            if map_idx < len(filenames):
                filename = filenames[map_idx]
                row[filename] = fh.getIntensity()
        rows.append(row)

    print(f"Total rows generated for DataFrame: {len(rows)}")
    # Crear DataFrame y ordenar columnas
    df = pd.DataFrame(rows)
    columns = ['rt', 'mz', 'intensity'] + filenames
    df = df[columns]
    csv = df.to_csv(index=False)
    csv_path = os.path.join(output_dir, f"{matrix_name}_consensus_matrix.csv")
    with open(csv_path, 'w') as f:
        f.write(csv)
    print(f"Consensus matrix CSV saved to: {csv_path}")
    # for row in df.itertuples():
    #     print(row)
    return output_path, csv_path