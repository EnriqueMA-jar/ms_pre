import pyopenms as oms
import os

def set_feature_maps(feature_file_paths, output_dir):
    feature_maps = []
    for feature_file in feature_file_paths:
            
        file_path = os.path.join(output_dir, feature_file)
        feature_map = oms.FeatureMap()
        oms.FeatureXMLFile().load(file_path, feature_map)  
            
        # Check for unique IDs
        feature_map.setUniqueIds()
            
        # Store the filename as meta value for later reference
        feature_map.setMetaValue("source_file", feature_file)
        feature_maps.append(feature_map)
        print(f"  - Loaded: {feature_file} ({feature_map.size()} features)")
    # Use as reference the file with the highest number of features
    ref_index = feature_maps.index(sorted(feature_maps, key=lambda x: x.size())[-1])
    print(f"\nReference map: {feature_file_paths[ref_index]} (index: {ref_index})")
        
    return feature_maps, ref_index
        
def align_files(feature_file_paths, mzML_file_paths, resolution, output_dir, value):
    # Create feature maps
    feature_maps, ref_index = set_feature_maps(feature_file_paths, output_dir)


    # Set parameters for the aligner
    aligner = oms.MapAlignmentAlgorithmPoseClustering()
    aligner_par = aligner.getDefaults()
    
    # Base parameters (common for all)
    aligner_par.setValue("max_num_peaks_considered", -1)  # Consider all peaks
    aligner_par.setValue("pairfinder:distance_RT:max_difference", 100.0)  # 100 seconds

    if resolution == 'High Resolution':
        # For: Orbitrap, FT-ICR, Q-TOF, TOF
        print(f"high res float(value) = {float(value)}")
        aligner_par.setValue("pairfinder:distance_MZ:max_difference", float(value))  # 10 ppm
        aligner_par.setValue("pairfinder:distance_MZ:unit", "ppm")
        
          
    elif resolution == 'Low Resolution':
        
        aligner_par.setValue("pairfinder:distance_MZ:unit", "Da")
        print(f"low res float(value) = {float(value)}")

        aligner_par.setValue("pairfinder:distance_MZ:max_difference", float(value))  # 0.5-1.0 Da
        
    aligner.setParameters(aligner_par)
    aligner.setReference(feature_maps[ref_index])

    # Dictionary for transformation files
    transform_files = {}
    
    print("\nAligning feature maps...")
    
    for i, feature_map in enumerate(feature_maps):
        if i == ref_index:
            # The reference map does not need transformation
            source_file = str(feature_map.getMetaValue("source_file"))
            transform_files[source_file] = None
            print(f"  - {feature_file_paths[i]}: REFERENCE (no transformation)")
            continue
        
        transformation = oms.TransformationDescription()
        aligner.align(feature_map, transformation)
    
        # Save the transformation
        source_file = str(feature_map.getMetaValue("source_file"))    
        transform_files[source_file] = transformation
    
        # Apply the transformation
        transformer = oms.MapAlignmentTransformer()
        transformer.transformRetentionTimes(feature_map, transformation, True)
    
        print(f"  - {feature_file_paths[i]}: Aligned successfully")
        
    # output_paths
    aligned_feature_paths = []
    aligned_mzml_paths = []

    print("\nSaving aligned featureXML files...")
    for i, feature_map in enumerate(feature_maps):
        base_name = os.path.basename(feature_file_paths[i])
        aligned_file = os.path.join(output_dir, f"aligned_{base_name}")
        oms.FeatureXMLFile().store(aligned_file, feature_map)
        aligned_feature_paths.append(aligned_file)
        print(f"  - Saved: {aligned_file}")

    for i, mzML_file in enumerate(mzML_file_paths):
        base_name = os.path.basename(mzML_file)
        mzML_path = os.path.join(output_dir, base_name)

        # Check if the file exists
        if not os.path.exists(mzML_path):
            print(f"  - WARNING: {base_name} not found, skipping...")
            continue

        # Load the mzML file
        exp = oms.MSExperiment()
        oms.MzMLFile().load(mzML_path, exp)
        exp.sortSpectra(True)

        # Get the corresponding transformation
        feature_file = feature_file_paths[i]
        tran_description = transform_files.get(feature_file)

        # save the aligned mzML file
        aligned_mzML_path = os.path.join(output_dir, f"aligned_{base_name}")

        if tran_description is None:
            # Is the reference file, save directly
            oms.MzMLFile().store(aligned_mzML_path, exp)
            print(f" - {base_name}: REFERENCE (no changes)")
        else:
            # Apply the transformation
            transformer = oms.MapAlignmentTransformer()
            transformer.transformRetentionTimes(exp, tran_description, True)
            oms.MzMLFile().store(aligned_mzML_path, exp)
            print(f" - {base_name}: Aligned and saved")
        aligned_mzml_paths.append(aligned_mzML_path)
    return aligned_feature_paths, aligned_mzml_paths

def map_identifications(aligned_mzml_paths, aligned_feature_paths, output_dir):
    
    mapped_features = []

    for featurexml, mzml in zip(aligned_feature_paths, aligned_mzml_paths):
            
        
        exp = oms.MSExperiment()
        oms.MzMLFile().load(mzml, exp)
        feature_map = oms.FeatureMap()
        oms.FeatureXMLFile().load(featurexml, feature_map)
            
        mapper = oms.IDMapper()
        peptide_ids = []
        protein_ids = []
        params = mapper.getParameters()
            
        use_centroid_rt = False
        use_centroid_mz = True
        mapper.annotate(feature_map, peptide_ids, protein_ids, use_centroid_rt, use_centroid_mz, exp)
            
        base_name = os.path.basename(featurexml)
        # oms.FeatureXMLFile().store(os.path.join(output_dir, f"mapped_{os.path.basename(featurexml)}"), feature_map)
            
        mapped_feature = os.path.join(output_dir, f"mapped_{base_name}")
        mapped_features.append(mapped_feature)
        oms.FeatureXMLFile().store(mapped_feature, feature_map)
    
    return mapped_features
    
    
def get_instruments(feature_file_paths, mzML_file_paths, output_dir):
    features_instruments = []
    mzml_instruments = []
    for feature_file in feature_file_paths:
        file_path = os.path.join(output_dir, feature_file)
        feature_map = oms.FeatureMap()
        oms.FeatureXMLFile().load(file_path, feature_map)  
        instrument = feature_map.getInstrument()
        features_instruments.append(instrument)
    for mzML_file in mzML_file_paths:
        file_path = os.path.join(output_dir, mzML_file)
        mzml_map = oms.MzMLFile()
        mzml_map.load(file_path)
        instrument = mzml_map.getInstrument()
        mzml_instruments.append(instrument)
    return features_instruments, mzml_instruments