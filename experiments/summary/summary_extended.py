from pyopenms import MSExperiment, MzMLFile, FileHandler
import time
import os
from collections import defaultdict

def get_file_info_extended(file_path):
    """
    Replica la funcionalidad del comando FileInfo de OpenMS
    """
    start_time = time.time()
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        print(f"Error: Archivo '{file_path}' no encontrado")
        return
    
    # Obtener tamaño del archivo
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    # Cargar el archivo silenciosamente
    exp = MSExperiment()
    MzMLFile().load(file_path, exp)
    
    #print("\n-- General information --")
    #print(f"File name: {os.path.basename(file_path)}")
    #print(f"File type: mzML")
    
    # Información del instrumento
    try:
        instrument = exp.getInstrument()
        if instrument is not None:
            #print(f"Instrument: {instrument.getName()}")
            
            # Información del analizador de masa
            for analyzer in instrument.getMassAnalyzers():
                analyzer_type = analyzer.getType()
                resolution = analyzer.getResolution()
                #print(f"  Mass Analyzer: {analyzer_type} (resolution: {resolution})")
        else:
            print("Instrument: Unknown")
    except:
        print("Instrument: Unknown")
    
    # Análisis de espectros
    ms_levels = defaultdict(int)
    total_peaks = 0
    all_rt = []
    all_mz = []
    all_intensity = []
    
    profile_by_level = defaultdict(int)
    centroid_by_level = defaultdict(int)
    ionization_method = None
    polarity = None
    
    # Procesar cada espectro
    for spec in exp:
        polarity = spec.getInstrumentSettings().getPolarity()
        ms_level = spec.getMSLevel()
        ms_levels[ms_level] += 1
        
        # Obtener datos de picos
        if spec.size() > 0:
            try:
                mz_array, intensity_array = spec.get_peaks()
                total_peaks += len(mz_array)
                
                if len(mz_array) > 0:
                    all_mz.extend(mz_array)
                    all_intensity.extend(intensity_array)
                
                # Determinar tipo de datos por nivel MS
                spec_type = spec.getType()
                if spec_type == 0:  # Profile
                    profile_by_level[ms_level] += 1
                elif spec_type == 1:  # Centroid
                    centroid_by_level[ms_level] += 1
                else:
                    # Estimación basada en densidad
                    if len(mz_array) > 1:
                        mz_range = mz_array[-1] - mz_array[0]
                        if mz_range > 0:
                            density = len(mz_array) / mz_range
                            if density > 10:
                                profile_by_level[ms_level] += 1
                            else:
                                centroid_by_level[ms_level] += 1
            except:
                pass
        
        # Tiempo de retención
        rt = spec.getRT()
        if 0 < rt < 1e6:  # Filtrar valores extremos
            all_rt.append(rt)
    
    ms_levels_sorted = sorted(ms_levels.keys())
    # Ranges
    if all_rt:
        rt_min, rt_max = min(all_rt), max(all_rt)
    else:
        rt_min, rt_max = None, None
    if all_mz:
        mz_min, mz_max = min(all_mz), max(all_mz)
    else:
        mz_min, mz_max = None, None
    if all_intensity:
        int_min, int_max = min(all_intensity), max(all_intensity)
    else:
        int_min, int_max = None, None

    # Spectra per MS level
    spectra_per_level = {level: ms_levels[level] for level in ms_levels_sorted}

    # Peak type per MS level
    peak_types = {}
    for level in ms_levels_sorted:
        profile_count = profile_by_level[level]
        centroid_count = centroid_by_level[level]
        if profile_count > centroid_count:
            peak_type = "Profile"
            if centroid_count > 0:
                peak_type += " (Centroid)"
        elif centroid_count > profile_count:
            peak_type = "Centroid"
            if profile_count > 0:
                peak_type += " (Profile)"
        else:
            peak_type = "Mixed"
        peak_types[level] = peak_type

    # Activation methods (MS2+)
    activation_methods = set()
    has_ms2_plus = any(spec.getMSLevel() > 1 for spec in exp)
    if has_ms2_plus:
        for spec in exp:
            if spec.getMSLevel() > 1:
                for precursor in spec.getPrecursors():
                    for method in precursor.getActivationMethods():
                        activation_methods.add(str(method))
    activation_methods = sorted(activation_methods)

    # Precursor charge distribution (MS2+)
    precursor_charges = {}
    if has_ms2_plus:
        charges = defaultdict(int)
        for spec in exp:
            if spec.getMSLevel() > 1:
                for precursor in spec.getPrecursors():
                    charge = precursor.getCharge()
                    if charge > 0:
                        charges[charge] += 1
        precursor_charges = dict(charges)

    # Chromatogram info
    num_chroms = exp.getNrChromatograms()
    chrom_types = {}
    total_chrom_peaks = 0
    if num_chroms > 1 or (num_chroms == 1 and len(ms_levels) > 1):
        if num_chroms > 0:
            types = defaultdict(int)
            for chrom in exp.getChromatograms():
                total_chrom_peaks += chrom.size()
                chrom_type = "unknown"
                try:
                    if chrom.getNativeID().lower().find('tic') != -1:
                        chrom_type = "total ion current chromatogram"
                    elif chrom.getNativeID().lower().find('bpc') != -1:
                        chrom_type = "base peak chromatogram"
                    else:
                        chrom_type = "total ion current chromatogram"
                except:
                    chrom_type = "total ion current chromatogram"
                types[chrom_type] += 1
            chrom_types = dict(types)

    # Instrument info
    instrument_name = None
    analyzers = []
    try:
        instrument = exp.getInstrument()
        if instrument is not None:
            instrument_name = instrument.getName()
            ion_source = instrument.getIonSources()
            for source in ion_source:
                ionization_method = source.getIonizationMethod()
                print(f"Ionization Method: {ionization_method}")
            for analyzer in instrument.getMassAnalyzers():
                analyzers.append({
                    "type": analyzer.getType(),
                    "resolution": analyzer.getResolution()
                })
    except:
        instrument_name = None

    # Build summary dictionary
    summary = {
        "File name": os.path.basename(file_path),
        "File type": "mzML",
        "File size (MB)": file_size_mb,
        "Instrument": instrument_name,
        "Analyzers": analyzers,
        "RT range (sec)": (rt_min, rt_max),
        "m/z range": (mz_min, mz_max),
        "Intensity range": (int_min, int_max),
        "Spectra levels": ms_levels_sorted,
        "Spectra per level": spectra_per_level,
        "Peak types": peak_types,
        "Activation methods": activation_methods,
        "Precursor charges": precursor_charges,
        "Number of chromatograms": num_chroms,
        "Chromatogram types": chrom_types,
        "Total chromatogram peaks": total_chrom_peaks,
        "Total peaks": total_peaks,
        "Elapsed time (sec)": time.time() - start_time,
        "Ionization method": ionization_method if ionization_method else None,
        "Polarity": polarity
    }
    
    return summary
# def plot_type(file_path):
#     summary = get_file_info_extended(file_path)
#     peak_types = summary.get("peak_types", {})
#     # Si hay algún nivel con Profile predominante, devolvemos Profile
#     for level, peak_type in peak_types.items():
#         if "Profile" in peak_type:
#             return "Profile"
#     # Si todos los niveles son Centroid, devolvemos Centroid
#     if peak_types and all("Centroid" in pt for pt in peak_types.values()):
#         return "Centroid"
#     # Si hay mezcla o no se puede determinar, devolvemos Profile por seguridad
#     return "Profile"
        

#get_file_info_extended("uploads/centroiding/Col_1.mzML")