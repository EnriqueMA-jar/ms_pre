import pyopenms as oms
import os

def get_gnps_files(mzML_file_paths, consensus_file, output_dir):
    not_ms2 = []
    output_files = []
    alert = None
    for mzML in mzML_file_paths:
        exp = oms.MSExperiment()
        oms.MzMLFile().load(mzML, exp)
        ms_levels = exp.getMSLevels()
        
        if 2 not in ms_levels:
            not_ms2.append(os.path.basename(mzML))
    alert = f"Error: The following mzML files do not contain MS2 spectra: {', '.join(not_ms2)}. Ensure you're using a valid mzML file." if not_ms2 else None

    if len(not_ms2) == 0:
        print("All mzML files contain MS2 spectra.")
        consensus_map = oms.ConsensusMap()
        oms.ConsensusXMLFile().load(consensus_file, consensus_map)
        filtered_map = oms.ConsensusMap(consensus_map)
        filtered_map.clear(False)

        for feature in consensus_map:
            if feature.getPeptideIdentifications():
                filtered_map.push_back(feature)

    # print("Consensus file:", consensus_file)
    # print("mzML files:", mzML_file_paths)
    # print("Features in filtered_map:", filtered_map.size())

        basename = os.path.basename(consensus_file)
        base_no_ext = os.path.splitext(basename)[0]

        consensusXML_file = os.path.join(output_dir, f"filtered_{base_no_ext}.consensusXML")
        oms.ConsensusXMLFile().store(consensusXML_file, filtered_map)

        mgf_file = os.path.join(output_dir, f"MS2data_{base_no_ext}.mgf")
    # Debugging/validation prints to help diagnose empty MGF output
    # print("--- GNPS MGF generation debug ---")
    # print(f"Consensus file to use: {consensusXML_file}")
    # print(f"Output MGF file: {mgf_file}")
    # print(f"Number of features in filtered_map: {filtered_map.size()}")
    # Check mzML paths exist and show first few
        for idx, mz in enumerate(mzML_file_paths):
            exists = os.path.exists(mz)
            print(f"mzML[{idx}]: {mz} exists={exists}")
    # Print first up to 10 consensus features and any peptide identifications
        max_preview = 10
        for i, cf in enumerate(filtered_map):
            if i >= max_preview:
                break
            try:
                pep_ids = cf.getPeptideIdentifications()
                pep_info = []
                for pid in pep_ids:
                    for hit in pid.getHits():
                        seq = hit.getSequence().toString() if hasattr(hit, 'getSequence') else str(hit)
                        pep_info.append(seq)
            except Exception:
                pep_info = []
            print(f"CF[{i}] RT={cf.getRT():.2f} mz={cf.getMZ():.4f} intensity={cf.getIntensity():.2f} peptide_ids_count={len(pep_info)} peptides={pep_info}")

    # GNPSMGFFile.store in pyOpenMS is picky about types: use oms.String for strings and
    # a list of encoded paths (bytes) for mzML list as used elsewhere in the codebase.
        try:
            oms.GNPSMGFFile().store(
                oms.String(consensusXML_file),
                [file.encode() for file in mzML_file_paths],
                oms.String(mgf_file),
            )
        except AssertionError as ae:
            print(f"AssertionError calling GNPSMGFFile.store: {ae}")
            raise
        except Exception as e:
            print(f"Error calling GNPSMGFFile.store: {e}")
            raise

        quant_file = os.path.join(output_dir, f"{basename}_FeatureQuantificationTable.txt")
        oms.GNPSQuantificationFile().store(filtered_map, quant_file)

        meta_file = os.path.join(output_dir, f"{basename}_MetaValueTable.tsv")
        oms.GNPSMetaValueFile().store(filtered_map, meta_file)

    # Annotate using the filtered map
        ion_net = oms.IonIdentityMolecularNetworking()
        ion_net.annotateConsensusMap(filtered_map)
        supp_file = os.path.join(output_dir, f"{basename}_SupplementaryPairTable.csv")
        ion_net.writeSupplementaryPairTable(filtered_map, supp_file)

        output_files = [
            consensusXML_file,
            mgf_file,
            quant_file,
            meta_file,
        # supp_file, SKIP SUPPLEMENTARY TABLE - IT DIDNT WORK
        ]
    return output_files, alert
    