import os
import pyopenms as oms

def centroid_file(file_path, output_dir):
    """
    Convert an mzML file in profile mode to centroid mode
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist")
    
    os.makedirs(output_dir, exist_ok=True)
    
    input_filename = os.path.basename(file_path)
    output_filename = os.path.splitext(input_filename)[0] + "_centroided.mzML"
    output_file = os.path.join(output_dir, output_filename)
    
    print(f"Processing: {file_path}")
    print(f"Output: {output_file}")
    
    # Cargar datos
    profile_spectra = oms.MSExperiment()
    oms.MzMLFile().load(file_path, profile_spectra)
    print(f"Número de espectros cargados: {profile_spectra.size()}")
    
    # Centroidizar 
    centroided_spectra = oms.MSExperiment()
    picker = oms.PeakPickerHiRes()
    picker.pickExperiment(profile_spectra, centroided_spectra, True)
    
    # Guardar
    oms.MzMLFile().store(output_file, centroided_spectra)
    print("Centroiding successful.")
    print(f"Centroid file stored: {output_file}")
    
    return output_file