import pyopenms as oms
import os
import plotly.graph_objects as go
import numpy as np

def detect_features(file_paths, mass_error_ppm, noise_threshold_int, features_type):
    
    # Detect if all files are already features
    all_are_features = all(".featureXML" in file for file in file_paths)

    if all_are_features:
        output_paths = file_paths
    else:
        output_paths = []
        if features_type == 'Metabolomics':
            for input_path in file_paths:
                # Load mzML file
                exp = oms.MSExperiment()
                oms.MzMLFile().load(input_path, exp)

                # Sort spectra by retention time
                exp.sortSpectra(True)
    
                # Initialize mass trace detection
                mass_traces = []
                mtd = oms.MassTraceDetection()
                mtd_params = mtd.getDefaults()
    
                # Set detection parameters
                mtd_params.setValue("mass_error_ppm", float(mass_error_ppm)) # Mass error in ppm
                mtd_params.setValue("dalton_error", 0.0)  # Absolute mass error in Da (set to 0 if using ppm)
                mtd_params.setValue("noise_threshold_int", float(noise_threshold_int))  # Noise threshold
                mtd.setParameters(mtd_params)
    
                # Detect mass traces
                mtd.run(exp, mass_traces, 0)
    
                # Initialize elution peak detection
                mass_traces_split = []
                mass_traces_final = []
                epd = oms.ElutionPeakDetection()
                epd_params = epd.getDefaults()
                epd_params.setValue("width_filtering", "fixed")  # Peak width filtering
                epd.setParameters(epd_params)
    
                # Detect elution peaks
                epd.detectPeaks(mass_traces, mass_traces_split)
    
                # If peak width filtering is automatic, filter the traces
                if epd.getParameters().getValue("width_filtering") == "auto":
                    epd.filterByPeakWidth(mass_traces_split, mass_traces_final)
                else: 
                    mass_traces_final = mass_traces_split
        
                # Initialize FeatureFindingMetabo to find features
                fm = oms.FeatureMap()
                feat_chrom = []
                ffm = oms.FeatureFindingMetabo()
    
                # Set FeatureFindingMetabo parameters
                ffm_params = ffm.getDefaults()
                ffm_params.setValue("isotope_filtering_model", "none")
                ffm_params.setValue("remove_single_traces", "true")  # Remove single traces
    
                # Filter traces with only one peak
                ffm_params.setValue("mz_scoring_by_elements", "false")
                ffm_params.setValue("report_convex_hulls", "true")
                ffm.setParameters(ffm_params)
    
                # Run feature detection
                ffm.run(mass_traces_final, fm, feat_chrom)
    
                # Set unique identifiers
                fm.setUniqueIds()
                fm.setPrimaryMSRunPath([input_path.encode()])
    
                # Define output path
                output_paths.append(input_path.replace(".mzML", "_Metabolomics_features.featureXML"))
    
                # Save the result to a FeatureXML file
                oms.FeatureXMLFile().store(output_paths[-1], fm)
                
                
        elif features_type == 'Proteomics':
            for input_path in file_paths:
                try:
                    # Cargar solo espectros MS1 para ahorrar memoria
                    options = oms.PeakFileOptions()
                    options.setMSLevels([1])  # Solo MS1

                    # Leer el archivo mzML
                    fh = oms.MzMLFile()
                    fh.setOptions(options)
                    input_map = oms.MSExperiment()
                    fh.load(input_path, input_map)
                    input_map.updateRanges()

                    # Verificar que hay espectros MS1
                    if input_map.getNrSpectra() == 0:
                        print(f"[ERROR] No MS1 spectra found in {input_path}")
                        continue

                    # Inicializar y ejecutar FeatureFinderAlgorithmPicked
                    ff = oms.FeatureFinderAlgorithmPicked()
                    out_features = oms.FeatureMap()
                    seeds = oms.FeatureMap()  # No se usan semillas en este caso

                    # Obtener y configurar parámetros
                    params = ff.getParameters()
                    # Puedes ajustar parámetros aquí si es necesario
                    # params.setValue("some_param", value)

                    ff.run(input_map, out_features, params, seeds)

                    # Verificar si se detectaron features
                    if out_features.size() == 0:
                        print(f"[WARN] No features detected in {input_path}")

                    # Define output path
                    output_file = input_path.replace(".mzML", "_Proteomics_features.featureXML")
                    output_paths.append(output_file)

                    # Asignar IDs únicos y guardar en archivo
                    out_features.setUniqueIds()
                    oms.FeatureXMLFile().store(output_file, out_features)

                    # Verificar que el archivo se creó
                    if not os.path.exists(output_file):
                        print(f"[ERROR] FeatureXML file not created: {output_file}")
                except Exception as e:
                    print(f"[ERROR] Exception processing {input_path}: {e}")


    return output_paths, all_are_features, features_type

def plot_features(file_paths, mass_error_ppm, noise_threshold_int, input_dir, features_type):
    output_files, all_are_features, features_type = detect_features(file_paths, mass_error_ppm, noise_threshold_int, features_type)
    # Directory containing the input files
    feature_files = output_files

    # Load each FeatureXML file into a FeatureMap
    original_maps = []
    for feature_file in feature_files:
        feature_map = oms.FeatureMap()
        oms.FeatureXMLFile().load(os.path.join(input_dir, feature_file), feature_map)
        original_maps.append(feature_map)

    # Set up colors for plotting
    import plotly.colors as pc
    base_colors = pc.qualitative.Plotly
    # If there are more files than colors, repeat the palette or generate colors
    num_files = len(feature_files)
    if num_files <= len(base_colors):
        colors = base_colors[:num_files]
    else:
        # Generate additional colors using the hsv palette
        import matplotlib.colors as mcolors
        colors = [mcolors.rgb2hex(mcolors.hsv_to_rgb((i/num_files, 0.7, 0.9))) for i in range(num_files)]

    # Create the figure
    fig = go.Figure()

    # Process each feature map
    for i, feature_map in enumerate(original_maps):
        rt = [f.getRT() for f in feature_map]
        mz = [f.getMZ() for f in feature_map]
        intensity = [f.getIntensity() for f in feature_map]
        # Normalize intensities for point size
        max_intensity = max(intensity) if intensity else 1
        normalized_intensity = np.array(intensity) / max_intensity
        # Create marker sizes based on intensity
        marker_sizes = normalized_intensity * 15 + 5  # Size between 5 y 20
        # Add scatter plot for each file
        fig.add_trace(
            go.Scatter(
                x=rt,
                y=mz,
                mode='markers',
                name=feature_files[i].split('/')[-1].replace('.featureXML', ''),
                marker=dict(
                    color=colors[i],
                    size=marker_sizes,
                    opacity=0.7,
                    line=dict(width=0.5, color='darkgray')
                ),
                hovertemplate="<b>%{fullData.name}</b><br>" +
                          "<b>RT:</b> %{x:.2f} s<br>" +
                          "<b>m/z:</b> %{y:.4f}<br>" +
                          "<b>Intensity:</b> %{text}<br>" +
                          "<extra></extra>",
                text=[f"{int_val:.2e}" for int_val in intensity]
            )
        )

    # Configurar el layout una sola vez fuera del ciclo
    fig.update_layout(
        title={
            'text': "Features Map - FeatureXML",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'family': 'Arial'}
        },
        xaxis_title="Retention Time (RT)",
        yaxis_title="m/z",
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
    
    return output_files, fig
    