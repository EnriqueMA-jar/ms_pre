import os
import pyopenms as oms

def centroid_file(file_paths, output_dir):
    """
    Convert an mzML file in profile mode to centroid mode
    """
    if not all(os.path.isfile(f) for f in file_paths):
        raise FileNotFoundError(f"One or more files do not exist")

    os.makedirs(output_dir, exist_ok=True)

    output_files = []
    for file_path in file_paths:
        input_filename = os.path.basename(file_path)
        output_filename = os.path.splitext(input_filename)[0] + "_centroided.mzML"
        output_file = os.path.join(output_dir, output_filename)
        output_files.append(output_file)

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

    return output_files