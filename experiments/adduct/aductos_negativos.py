import pyopenms as poms
import pandas as pd

# Ruta del archivo de entrada
input_file = "/home/labi/Documents/Aquismon/Feature_Metabo/EO_01A_Centroide.featureXML"

# Ruta de salida para los resultados
output_dir = "/home/labi/Documents/Aquismon/Aductos"
output_file = f"{output_dir}/EO_01A_adducts_neg.tsv"

# Crear un FeatureMap y cargar el archivo de entrada
feature_map = poms.FeatureMap()
poms.FeatureXMLFile().load(input_file, feature_map)

# Inicializar MetaboliteFeatureDeconvolution
mfd = poms.MetaboliteFeatureDeconvolution()

# Obtener los parámetros predeterminados
params = mfd.getDefaults()

# Configurar aductos esperados NEGATIVOS
params.setValue("potential_adducts", ["H-1:-:0.6", "Cl-1:-:0.4", "CH2O2:-:0.2"])

# Configurar rango de carga y diferencias de tiempo de retención
params.setValue("charge_min", 1, "Minimal possible charge")
params.setValue("charge_max", 3, "Maximal possible charge")
params.setValue("charge_span_max", 3)
params.setValue("retention_max_diff", 3.0)
params.setValue("retention_max_diff_local", 3.0)

# Establecer los parámetros actualizados
mfd.setParameters(params)

# Crear estructuras para los resultados
feature_map_MFD = poms.FeatureMap()  # Mapa de características con aductos
groups = poms.ConsensusMap()         # Grupos de características
edges = poms.ConsensusMap()          # Conexiones entre características

# Ejecutar el modelo de detección de aductos
mfd.compute(feature_map, feature_map_MFD, groups, edges)

# Exportar los datos a un DataFrame de pandas
df = feature_map_MFD.get_df(export_peptide_identifications=False)
df["adduct"] = [f.getMetaValue("dc_charge_adducts") if f.metaValueExists("dc_charge_adducts") else None 
                for f in feature_map_MFD]

# Guardar el DataFrame como un archivo CSV
df.to_csv(output_file, sep="\t", index=False)

print(f"Resultados guardados en {output_file}")
