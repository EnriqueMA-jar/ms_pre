import pyopenms as oms

def map_identifications(mzml_file, featurexml_in, featurexml_out):
    """
    Esta función mapea identificaciones desde un archivo mzML (con espectros MS2) 
    a un FeatureMap, replicando la funcionalidad de `IDMapper -id empty.idXML`.
    
    Args:
        mzml_file (str): Ruta al archivo mzML alineado que contiene los espectros.
        featurexml_in (str): Ruta al archivo FeatureXML de entrada (alineado).
        featurexml_out (str): Ruta donde se guardará el FeatureXML con las identificaciones mapeadas.
    """
    
    # 1. Cargar el archivo mzML alineado con los espectros
    exp = oms.MSExperiment()
    oms.MzMLFile().load(mzml_file, exp)
    
    # 2. Cargar el FeatureMap (featureXML) que se va a anotar
    feature_map = oms.FeatureMap()
    oms.FeatureXMLFile().load(featurexml_in, feature_map)
    
    # 3. Inicializar el IDMapper
    mapper = oms.IDMapper()
    
    # 4. Crear las listas VACÍAS de identificaciones (equivalente a empty.idXML)
    peptide_ids = []
    protein_ids = []
    
    # 5. Configurar parámetros para el mapeo (opcional)
    params = mapper.getParameters()
    # params.setValue("rt_tolerance", 10.0)
    # params.setValue("mz_tolerance", 0.05)
    # mapper.setParameters(params)
    
    # 6. Ejecutar la anotación (mapeo)
    use_centroid_rt = False
    use_centroid_mz = True
    mapper.annotate(feature_map, peptide_ids, protein_ids, use_centroid_rt, use_centroid_mz, exp)
    
    # 7. Guardar el FeatureMap resultante
    oms.FeatureXMLFile().store(featurexml_out, feature_map)
    print(f"Proceso completado. FeatureMap con identificaciones guardado en: {featurexml_out}")

# Si quieres probarlo directamente:
if __name__ == "__main__":
    map_identifications('uploads/alignment/aligned_680_CD1-1neg_savgol_centroided.mzML', 'uploads/alignment/aligned_680_CD1-1neg_savgol_centroided_Metabolomics_features.featureXML', 'output.featureXML')
