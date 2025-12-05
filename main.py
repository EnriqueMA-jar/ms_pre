from datetime import datetime
from flask import Flask, render_template, request, session, redirect, send_file, jsonify, url_for, send_from_directory
import re
import os
import pandas as pd
# Import summary functions
from experiments.summary.summary import get_file_info
from experiments.tic.tic_2d_3d import main as plot_tic
from experiments.tic.tic_2d_3d import load_and_process_data
from experiments.summary.summary_extended import get_file_info_extended 

# Import chromatogram functions
from experiments.chromatograms.multiple_chromatograms import render_chromatogram_comparison as compare_chromatograms

# Import spectra functions
from experiments.spectra.spectra_binning import binning_spectrum
from experiments.spectra.merge_spectra import merge_spectra
from experiments.spectra.spectra_ms2 import render_spectra_plots

# Import the smoothing functions
from experiments.smoothing.multiple_smoothing import multiple_smoothing
from experiments.smoothing.single_smoothing import single_smoothing

# Import centroiding functions
from experiments.centroiding.centroiding import centroid_file

# Import normalization functions
from experiments.normalize.normalize_to_one import normalize_to_one
from experiments.normalize.normalize_to_tic import normalize_to_tic

# Import features functions
from experiments.features.features import plot_features

# Import adduct functions
from experiments.adduct.adduct import get_adduct_files

# Import alignment functions
from experiments.alignment.alignment import align_files, map_identifications

# Import Consensus functions
from experiments.consensus.consensus import get_consensus_matrix

# Import GNPS functions
from experiments.gnps.gnps import get_gnps_files

# Import Accurate Mass functions
from experiments.accurate_mass_search.accurate_mass import load_files as accurate_mass_search


app = Flask(__name__)
app.secret_key = '123'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 * 1024  
CHUNKS_DIR = 'uploads/temp_chunks' # default folder for file chunks
SMOOTHING_DIR = 'uploads/smoothing' # default folder for smoothing files
CENTROIDS_DIR = 'uploads/centroiding' # default folder for centroiding files
NORMALIZE_DIR = 'uploads/normalize' # default folder for normalization files
FEATURES_DIR = 'uploads/features' # default folder for features files
ADDUCTS_DIR = 'uploads/adducts' # default folder for adducts files
ALIGNMENT_DIR = 'uploads/alignment' # default folder for alignment files
CONSENSUS_DIR = 'uploads/consensus' # default folder for consensus files
GNPS_DIR = 'uploads/gnps' # default folder for gnps files
ACCURATE_MASS_DIR = 'uploads/accurate_mass' # default folder for accurate mass search files

ALL_UPLOAD_DIRS = [SMOOTHING_DIR, CENTROIDS_DIR, NORMALIZE_DIR, FEATURES_DIR, ADDUCTS_DIR, ALIGNMENT_DIR, CONSENSUS_DIR, GNPS_DIR, ACCURATE_MASS_DIR]

app.config['SESSION_PERMANENT'] = False

WORKFLOWS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'experiments/workflows/workflows.json')

# -------------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------------------------------------
# Large file upload endpoint/function ####################################
@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    """
    Endpoint para recibir y ensamblar archivos subidos en chunks.
    Espera los siguientes campos en el form-data:
    - chunk: el fragmento de archivo
    - filename: nombre original del archivo
    - upload_id: id único de la subida
    - chunk_index: índice del chunk
    - total_chunks: número total de chunks
    - target_dir: carpeta destino
    """
    try:
        chunk = request.files['chunk']
        filename = request.form['filename']
        upload_id = request.form['upload_id']
        chunk_index = int(request.form['chunk_index'])
        total_chunks = int(request.form['total_chunks'])
        target_dir = request.form.get('target_dir', 'mzML_samples')

        # Carpeta temporal para los chunks de este archivo
        chunk_folder = os.path.join(CHUNKS_DIR, upload_id)
        os.makedirs(chunk_folder, exist_ok=True)

        # Guardar el chunk
        chunk_path = os.path.join(chunk_folder, f"chunk_{chunk_index}")
        chunk.save(chunk_path)

        # Revisar si ya se recibieron todos los chunks
        uploaded_chunks = len([name for name in os.listdir(chunk_folder) if name.startswith('chunk_')])
        if uploaded_chunks == total_chunks:
            # Ensamblar el archivo final
            os.makedirs(target_dir, exist_ok=True)
            assembled_path = os.path.join(target_dir, filename)
            print(f"[UPLOAD_CHUNK] All chunks received. Assembling to {assembled_path}")
            with open(assembled_path, 'wb') as assembled:
                for i in range(total_chunks):
                    part_path = os.path.join(chunk_folder, f"chunk_{i}")
                    with open(part_path, 'rb') as part:
                        assembled.write(part.read())
            # Limpiar los chunks temporales
            for name in os.listdir(chunk_folder):
                os.remove(os.path.join(chunk_folder, name))
            os.rmdir(chunk_folder)
            # Guardar la ruta en sesión para el summary
            session['file_path'] = assembled_path
            print(f"[UPLOAD_CHUNK] Assembly complete. Returning file_path: {assembled_path}")
            return jsonify({'status': 'complete', 'file_path': assembled_path})
        else:
            return jsonify({'status': 'incomplete', 'received': uploaded_chunks, 'total': total_chunks})
    except Exception as e:
        print(f"[UPLOAD_CHUNK] Error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500
# -------------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------------------------------------------------
# Workflow management  ####################################

# Index page ####################################
@app.route('/')
def home():
    return redirect('/index')

@app.route('/index')
def index():
    return render_template('index.html', page='Home')

@app.route('/functions_hub')
def functions_hub():
    return render_template('functions_hub.html', page='Functions Hub', workflows_file=WORKFLOWS_FILE)

# Alignment page ####################################
@app.route('/alignment', methods=['GET', 'POST'])
def alignment():
    if 'alignment' in session.get('current_steps', []) and session.get('step_status') == 'finished':
        session['step_status'] = 'started'
    selected_option = request.form.get('alignment_options', 'op1')
    return render_template('alignment.html', selected_option=selected_option, page='Alignment')

# Alignment endpoint/function ####################################
@app.route('/get_files_alignment', methods=['POST', 'GET'])
def process_alignment():
     # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), ALIGNMENT_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    
    # Check which option is selected
    selected_option = request.form.get('selected_option', 'op1')
    if not selected_option:
        selected_option = 'op1'
        
    feature_files = request.files.getlist('feature_filename')
    mzml_files = request.files.getlist('mzml_filename')
    

    # Save files and get their paths
    feature_file_paths = []
    for file in feature_files:
        path = os.path.join(uploads_dir, file.filename)
        if not os.path.exists(path):
            file.save(path)
        feature_file_paths.append(path)
    mzml_file_paths = []
    for file in mzml_files:
        path = os.path.join(uploads_dir, file.filename)
        if not os.path.exists(path):
            file.save(path)
        mzml_file_paths.append(path)

    # Get base names without extension from mzML files
    mzml_basenames = [os.path.splitext(os.path.basename(f))[0] for f in mzml_file_paths]
    # Get base names without extension from feature files
    feature_basenames = [os.path.splitext(os.path.basename(f))[0] for f in feature_file_paths]
    # Check if the mzML base name is contained in any feature base name
    matches = [mzml for mzml in mzml_basenames if any(mzml in feat for feat in feature_basenames)]

    if selected_option == 'op1':
        resolution = 'High Resolution'
        value = request.form.get('ppm')
        if value is None or value == '':
            value = 10.0  # Default value for PPM
        else:
            value = float(value)
        # Main processing
        if len(matches) == len(feature_file_paths) and len(matches) == len(mzml_file_paths):
            download_links_features_paths, download_links_mzml_paths, ms_levels = align_files(feature_file_paths, mzml_file_paths, resolution, uploads_dir, value)
            
            # Generate Flask links for the template
            download_links_features = []
            download_links_mapped = []
            mapped_feature_paths = []
            
            if 2 in ms_levels:
                # Map identifications after alignment
                mapped_feature_paths = map_identifications(download_links_mzml_paths, download_links_features_paths, uploads_dir)
                success_alert = "Generated files for MS2 levels detected."
                
                for path in mapped_feature_paths:
                    filename = os.path.basename(path)
                    download_links_mapped.append(f"/uploads/alignment/{filename}")
            elif 2 not in ms_levels:
                success_alert = "Generated files only for MS1 levels detected."
            for path in download_links_features_paths:
                filename = os.path.basename(path)
                download_links_features.append(f"/uploads/alignment/{filename}")
            
            download_links_mzml = []
            for path in download_links_mzml_paths:
                filename = os.path.basename(path)
                download_links_mzml.append(f"/uploads/alignment/{filename}")
                
                
            # Store generated files in session for workflow tracking
            generated_files = []
            if len(mapped_feature_paths) > 0:
                for path in download_links_features_paths + mapped_feature_paths + download_links_mzml_paths:
                    generated_files.append({
                        "filename": os.path.basename(path),
                        "path": path
                    })
            else:
                for path in download_links_features_paths + download_links_mzml_paths:
                    generated_files.append({
                        "filename": os.path.basename(path),
                        "path": path
                    })
            workflow_step_finished('alignment', generated_files)
            #advance_workflow_step('alignment')

            return render_template('alignment.html', success_alert=success_alert, download_links_features=download_links_features, download_links_mapped=download_links_mapped, download_links_mzml=download_links_mzml, selected_option=selected_option, page='Alignment')
        else:
            session['step_status'] = 'started'
            error_alert = "Error: Not all feature files have a corresponding mzML file. Please check your uploads."
            return render_template('alignment.html', download_links_features=None, download_links_mapped=None, download_links_mzml=None, selected_option=selected_option, error_alert=error_alert, page='Alignment')

    elif selected_option == 'op2':
        resolution = 'Low Resolution'
        value = request.form.get('da')
        if value is None or value == '':
            value = 0.3  # Default value for Da
        else:
            value = float(value)
        if len(matches) == len(feature_file_paths) and len(matches) == len(mzml_file_paths):
            # Main processing
            download_links_features, download_links_mzml = align_files(feature_file_paths, mzml_file_paths, resolution, uploads_dir, value)
            # Store generated files in session for workflow tracking
            generated_files = []
            for path in download_links_features + download_links_mzml:
                filename = os.path.basename(path)
                generated_files.append({
                    "filename": filename,
                    "path": f"/uploads/alignment/{filename}"
                })
            workflow_step_finished('alignment', generated_files)
            return render_template('alignment.html', download_links_features=download_links_features, download_links_mapped=download_links_mapped, download_links_mzml=download_links_mzml, selected_option=selected_option, page='Alignment')
        else:
            session['step_status'] = 'started'
            alert = "Error: Not all feature files have a corresponding mzML file. Please check your uploads."
            return render_template('alignment.html', download_links_features=None, download_links_mzml=None, selected_option=selected_option, alert=alert, page='Alignment')

    #print("Coincidencias entre mzML y features:", matches)
    # return render_template('alignment.html', download_links=None, selected_option=selected_option)
    
# Consensus page ####################################
@app.route('/consensus', methods=['GET', 'POST'])
def consensus():
    if session.get('workflow_status') == 'started':
        if 'consensus' in session.get('current_steps', []) and session.get('step_status') == 'finished':
            session['step_status'] = 'started'
    return render_template('consensus.html', page='Consensus')

# Consensus endpoint/function ####################################
@app.route('/get_files_consensus', methods=['POST', 'GET']) 
def process_consensus():
    
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), CONSENSUS_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_paths = request.files.getlist('filename')
    
    if len(file_paths) < 2:
        error_alert = "Error: Please upload at least two .featureXML files to generate a consensus matrix."
        session['step_status'] = 'started'
        return render_template('consensus.html', error_alert=error_alert, page='Consensus')
    else:
        saved_file_paths = []
        for file in file_paths:
            path = os.path.join(uploads_dir, file.filename)
            if not os.path.exists(path):
                file.save(path)
            saved_file_paths.append(path)
        file_paths = saved_file_paths
    
        # get_consensus_matrix now returns (output_path, csv_path)
        result = get_consensus_matrix(file_paths, uploads_dir, "empty.idXML")
        if isinstance(result, tuple):
            output_path, csv_path = result
        else:
            output_path, csv_path = result, None

        download_links = []
        if output_path and os.path.exists(output_path):
            filename = os.path.basename(output_path)
            download_links.append(f"/uploads/consensus/{filename}")
        if csv_path and os.path.exists(csv_path):
            csv_filename = os.path.basename(csv_path)
            download_links.append(f"/uploads/consensus/{csv_filename}")

        if download_links:
            # Store generated files in session for workflow tracking
            generated_files = []
            for path in download_links:
                generated_files.append({
                    "filename": os.path.basename(path),
                    "path": path
                })
            workflow_step_finished('consensus', generated_files)
            #advance_workflow_step('consensus')
            return render_template('consensus.html', download_links_consensus=download_links, page='Consensus')
        else:
            session['step_status'] = 'started'
            error_alert = "Error: Consensus file could not be generated. Please check your uploads."
            return render_template('consensus.html', error_alert=error_alert, page='Consensus')

# Features page ####################################
@app.route('/features', methods=['GET', 'POST'])
def features():
    
    if session.get('workflow_status') == 'started':
        if 'features' in session.get('current_steps', []) and session.get('step_status') == 'finished':
            session['step_status'] = 'started'
        #session['generated_files'] = []
    
    print("Current steps before:", session.get('current_steps', []))
    selected_option = request.form.get('features_options', 'op1')
    return render_template('features.html', selected_option=selected_option, page='Features')

# FEATURES Endpoint for serving files from the uploads folder ####################################
@app.route('/get_files_features', methods=['POST', 'GET'])
def features_function():
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), FEATURES_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Check which option is selected
    selected_option = request.form.get('features_options') or session.get('selected_option_features', 'op1')
    session['selected_option_features'] = selected_option
    
    files = request.files.getlist('filename')
    mass_error_ppm = request.form.get('mass_error_ppm', 10)
    noise_threshold_int = request.form.get('noise_threshold_int', 1000)
    download_links = []

    # if theres files uploaded, use them, otherwise use the ones in the session
    if files and any(file.filename for file in files):
        file_paths = []
        for file in files:
            path = os.path.join(uploads_dir, file.filename)
            if not os.path.exists(path):
                file.save(path)
            file_paths.append(path)
        session['file_paths'] = file_paths
    else:
        file_paths = session.get('file_paths', [])

    # Convertir parámetros a float/int según lo que espera detect_features
    try:
        mass_error_ppm = float(mass_error_ppm)
    except Exception:
        mass_error_ppm = 10.0
    try:
        noise_threshold_int = int(noise_threshold_int)
    except Exception:
        noise_threshold_int = 1000

    # Determinar el tipo de features
    if selected_option == 'op1':
        features_type = 'Metabolomics'
    elif selected_option == 'op2':
        features_type = 'Proteomics'
    

    # Procesar todos los archivos juntos para que la gráfica incluya todos
    output_files, plot_features_detected = plot_features(file_paths, mass_error_ppm, noise_threshold_int, uploads_dir, features_type)
    import plotly.io as pio
    plot_features_render = pio.to_html(plot_features_detected, full_html=False, include_plotlyjs='cdn')

    # Verificar si todos los archivos ya son .featureXML
    all_are_features = all([f.endswith('.featureXML') for f in file_paths])

    if all_are_features:
        # Solo mostrar el gráfico, sin links
        output_paths = file_paths
        # Store generated files in session for workflow tracking
        generated_files = []
        for path in download_links:
            generated_files.append({
                "filename": os.path.basename(path),
                "path": path
            })
        workflow_step_finished('features', generated_files)
        #advance_workflow_step('features')
        return render_template('features.html', plot_features=plot_features_render, download_links=None, selected_option=selected_option, page='Features')
    
    elif output_files and len(output_files) > 0:
        # Generar links de descarga para todos los archivos generados
        for output_file in output_files:
            if output_file and os.path.exists(output_file):
                filename = os.path.basename(output_file)
                download_link = f"/uploads/features/{filename}"
                download_links.append(download_link)
            else:
                print(f"[ERROR] No se generó archivo de features para {output_file}")
        session['file_paths'] = file_paths
        # Store generated files in session for workflow tracking
        generated_files = []
        for path in download_links:
            generated_files.append({
                "filename": os.path.basename(path),
                "path": path
            })
        workflow_step_finished('features', generated_files)
        #advance_workflow_step('features')
        return render_template('features.html', plot_features=plot_features_render, download_links=download_links, selected_option=selected_option, page='Features')
    else:
        alert = 'There are no features detected.'
        session['step_status'] = 'started'
        return render_template('features.html', plot_features=plot_features_render, download_links=None, error_alert=alert, selected_option=selected_option, page='Features')

# GNPS page ####################################
@app.route('/gnps', methods=['GET', 'POST'])
def gnps():
    return render_template('gnps.html', page='GNPS')

# GNPS Endpoint for serving files from the uploads folder ####################################
@app.route('/get_files_gnps', methods=['POST', 'GET'])
def process_gnps():
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), GNPS_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    output_files = []
    download_links = []
    mzml_file_paths = []

    aligned_mzML_files = request.files.getlist("mzml_filename")
    consensus_file = request.files["consensus_filename"]
    
    if len(aligned_mzML_files) < 1 or not consensus_file:
        error_alert = "Error: Please upload at least one aligned .mzML file and one .consensusXML file to generate GNPS files."
        return render_template('gnps.html', error_alert=error_alert, page='GNPS')
    else:
        
        for file in aligned_mzML_files:
            path = os.path.join(uploads_dir, file.filename)
            if not os.path.exists(path):
                file.save(path)
            mzml_file_paths.append(path)
            
        consensus_path = os.path.join(uploads_dir, consensus_file.filename)
        consensus_file.save(consensus_path)

        output_files, alert = get_gnps_files(mzml_file_paths, consensus_path, uploads_dir)
        if alert is not None:
            return render_template('gnps.html', warning_alert=alert, page='GNPS')
        elif alert is None:
            for output_file in output_files:
                if output_file and os.path.exists(output_file):
                    filename = os.path.basename(output_file)
                    download_link = f"/uploads/gnps/{filename}"
                    download_links.append(download_link)
            # Store generated files in session for workflow tracking
            generated_files = []
            for path in download_links:
                generated_files.append({
                    "filename": os.path.basename(path),
                    "path": path
                })
            workflow_step_finished('gnps', generated_files)
            #advance_workflow_step('gnps')
            return render_template('gnps.html', download_links_gnps=download_links, page='GNPS')

        return render_template('gnps.html', download_links_gnps=download_links, page='GNPS')


# Chromatograms page ####################################
@app.route('/chromatograms')
def chromatograms():
    return render_template('chromatogram.html', page='Chromatograms')

# render chromatograms endpoint/function ####################################
@app.route('/get_files_chromatograms', methods=['POST'])
def process_chromatograms():
    # Check if files are uploaded
    if 'filename' in request.files:
        files = request.files.getlist('filename')
        intensity_threshold = 100
        file_paths = []
        for file in files:
            path = f"mzML_samples/{file.filename}"
            file.save(path)
            file_paths.append(path)
        session['file_paths'] = file_paths
        print("Rutas de archivos:", file_paths)
    else:
        file_paths = session.get('file_paths', [])
        intensity_threshold = int(request.form.get('intensity_threshold', 100))

    # Generate chromatogram plot 
    import plotly.io as pio
    fig = compare_chromatograms(file_paths, intensity_threshold)
    plot_chromatograms = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

    # If AJAX request, return only the plot HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        
        #print("AJAX request detected")
        #print("Rutas de archivos:", file_paths)
        return plot_chromatograms
    # If not, return the full page
    return render_template('chromatogram.html', plot_chromatograms=plot_chromatograms, page='Chromatograms')
    
# normalize page ####################################
@app.route('/normalize', methods=['GET', 'POST'])
def normalize():
    selected_option = request.form.get('normalization_options', 'op1')
    return render_template('normalize.html', selected_option=selected_option, page='Normalize')

# render normalize endpoint/function ####################################
@app.route('/get_files_normalize', methods=['POST'])
def process_normalize():
    plot_normalized = None
    plot_original = None
    download_link = None

    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), NORMALIZE_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    selected_option = request.form.get('normalization_options') or session.get('selected_option_normalize', 'op1')
    session['selected_option_normalize'] = selected_option
    
    # check if theres a file in the request
    uploaded_file = request.files.get('filename')
    file_path = None
    
    if uploaded_file and uploaded_file.filename:
        file_path = os.path.join(uploads_dir, uploaded_file.filename)
        uploaded_file.save(file_path)
        session['file_path'] = file_path
    else:
        file_path = session.get('file_path')

    # Only proceed if file_path is set
    if not file_path:
        return render_template('normalize.html', selected_option=selected_option, plot_original=None, plot_normalized=None, download_link=None, error_msg="No file uploaded.", page='Normalize')

    if selected_option == 'op1':
        result = normalize_to_one(file_path)
    elif selected_option == 'op2':
        result = normalize_to_tic(file_path)
    
    if isinstance(result, tuple):
        fig, fig2, output_path = result
    else:
        fig, fig2, output_path = None, None, result

    plot_original = None
    plot_normalized = None
    download_link = None

    if output_path and "normalized" in output_path:
        filename = os.path.basename(output_path)
        download_link = f"{NORMALIZE_DIR}/{filename}"
        print(f"Download link: {download_link}")
        if fig is not None and fig2 is not None:
            import plotly.io as pio
            plot_original = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
            plot_normalized = pio.to_html(fig2, full_html=False, include_plotlyjs='cdn')

    return render_template('normalize.html', selected_option=selected_option, plot_original=plot_original, plot_normalized=plot_normalized, download_link=download_link, page='Normalize')

# render spectra page ####################################
@app.route('/spectra')
def spectra():
    return render_template('spectra.html',  
        ms_level=0, 
        ms_type=0,
        spectrum_value=0,
        filename='',
        plot_spectra=None,
        plot_merge_spectrum=None, page='Spectra')

# render spectra endpoint/function (unificado) ####################################
@app.route('/get_files_spectra', methods=['POST'])
def process_spectra():
    import plotly.io as pio
    import pyopenms as oms
    
    # Check if files are uploaded
    if 'filename' in request.files:
        file = request.files['filename']
        spectrum_value = 250
        # Guardar en uploads/temp_chunks
        chunk_dir = os.path.join('uploads', 'temp_chunks')
        os.makedirs(chunk_dir, exist_ok=True)
        path = os.path.join(chunk_dir, file.filename)
        # Si el archivo ya existe (por chunks), no lo volvemos a guardar
        if not os.path.exists(path):
            file.save(path)
        session['file_path'] = path
        filename = file.filename
        # print("Ruta de archivos:", path)
    else:
        # if there is no new file, get the previous one from the session, and the spectrum index from the set value input
        path = session.get('file_path')
        filename = os.path.basename(path) if path else ''
        spectrum_value = int(request.form.get('spectrum_value', 100))
        
    # Check MS level
    exp = oms.MSExperiment()
    oms.MzMLFile().load(path, exp)
    spectra = exp.getSpectra()
    
    # Contar MS levels directamente (sin regex ni llamar a get_file_info)
    ms1 = sum(1 for s in spectra if s.getMSLevel() == 1)
    ms2 = sum(1 for s in spectra if s.getMSLevel() == 2)
    
    # ========== MS1: Gráficas de binning y merge ==========
    if ms1 > 0 and ms2 == 0:
        ms_type = 1
        
        # Binning usando el experimento ya cargado
        alert, fig_binning, spectrum_index = binning_spectrum(exp, spectrum_value)
        if alert and fig_binning is None:
            return render_template('spectra.html', error_alert=alert, page='Spectra')
        
        plot_spectra = pio.to_html(fig_binning, full_html=False)
        
        # Merge usando el experimento ya cargado
        fig_merge = merge_spectra(exp)
        plot_merge_spectrum = pio.to_html(fig_merge, full_html=False)
        
        return render_template('spectra.html', 
            plot_spectra=plot_spectra, 
            plot_merge_spectrum=plot_merge_spectrum, 
            filename=filename, 
            ms_level=ms1, 
            ms_type=ms_type, 
            spectrum_value=spectrum_value, 
            page='Spectra')
    
    # ========== MS2: Gráficas de comparación MS1 vs MS2 ==========
    elif ms2 > 0:
        ms_type = 2
        
        # Render plots usando el experimento ya cargado
        fig_ms2_spectra, fig_ms2_overlay = render_spectra_plots(exp)
        plot_ms2_spectra = pio.to_html(fig_ms2_spectra, full_html=False)
        plot_ms2_overlay = pio.to_html(fig_ms2_overlay, full_html=False)
        
        return render_template('spectra.html',
            plot_ms2_spectra=plot_ms2_spectra,
            plot_ms2_overlay=plot_ms2_overlay,
            filename=filename,
            ms_level=ms1,
            ms_type=ms_type,
            spectrum_value=spectrum_value, 
            page='Spectra')
    
    # Si no hay espectros válidos
    return render_template('spectra.html', error_alert="No valid MS1 or MS2 spectra found.", page='Spectra')

    
# Smoothing page ####################################
@app.route('/smoothing', methods=['GET', 'POST'])
def smoothing():
    selected_option = request.form.get('smoothing_options', 'op1')
    return render_template('smoothing.html', selected_option=selected_option, page='Smoothing')

# Smoothing endpoint/function ####################################
@app.route('/get_files_smoothing', methods=['POST'])
def process_smoothing():
    
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), SMOOTHING_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Check which option is selected
    selected_option = request.form.get('smoothing_options', 'op1')
    # print(f"[DEBUG] selected_option: {selected_option}")
    if selected_option == 'op1':
        # It could be a single file smoothing
        files = request.files.getlist('filename')
        file = None
        for f in files:
            if f and f.filename and f.filename.endswith('.mzML'):
                file = f
                break
        if not file:
            alert = 'Please upload a valid .mzML file for single file smoothing.'
            return render_template('smoothing.html', selected_option='op1', download_link=None, window_length=11, polyorder=3, error_alert=alert, page='Smoothing')
        # print(f"[DEBUG] single file: {file.filename}")
        save_path = os.path.join(uploads_dir, file.filename)
        if not os.path.exists(save_path):
            file.save(save_path)
        output_path = single_smoothing(save_path)
        if "savgol" in output_path:
            filename = os.path.basename(output_path)
            download_link = f"{SMOOTHING_DIR}/{filename}"
        return render_template('smoothing.html', selected_option='op1', download_link=download_link, window_length=11, polyorder=3, page='Smoothing')
    else:
        if selected_option == 'op2':
            window_length = request.form.get('window_length')
            polyorder = request.form.get('polyorder')
            if window_length is None or window_length == '':
                window_length = 11
            else:
                window_length = int(window_length)
            if polyorder is None or polyorder == '':
                polyorder = 3
            else:
                polyorder = int(polyorder)
            files = request.files.getlist('filename')
            # print(f"[DEBUG] multiple files count: {len(files)}")
            file_paths = []
            for file in files:
                # print(f"[DEBUG] processing file: {file.filename}")
                if file.filename.endswith('.mzML'):
                    save_path = os.path.join(uploads_dir, file.filename)
                    if not os.path.exists(save_path):
                        file.save(save_path)
                    file_paths.append(save_path)
                else:
                    alert = 'Please upload a valid .mzML file for multiple file smoothing.'
                    return render_template('smoothing.html', selected_option='op2', download_links=None, window_length=window_length, polyorder=polyorder, error_alert=alert, page='Smoothing')

            # Process files and get output paths
            output_files = multiple_smoothing(file_paths, window_length, polyorder)

            # Generate download links
            download_links = []
            for file_path in output_files:
                if "savgol" in file_path:
                    filename = os.path.basename(file_path)
                download_links.append(f"{SMOOTHING_DIR}/{filename}")

            # Render the page with download links and keep the multiple option selected
            return render_template('smoothing.html', selected_option='op2', download_links=download_links, page='Smoothing', window_length=window_length, polyorder=polyorder)
    


# Summary page ####################################
@app.route('/summary')
def summary():
    return render_template('summary.html', page='Summary')

@app.route('/get_file_info', methods=['POST'])
def process_mzML():
    file = request.files.get('file')
    filename = None

    if file:
        filename = file.filename
    elif 'filename' in request.form:
        filename = request.form.get('filename')

    # Validación de extensión
    if not filename or not filename.endswith('.mzML'):
        alert = "Invalid file type. Please upload a .mzML file."
        return render_template('summary.html', error_alert=alert, page='Summary')

    filter_type = request.form.get('filter_options', 'Plasma')

    # Determinar la ruta real del archivo
    if file:
        path = os.path.join('mzML_samples', filename)
        session['file_path'] = path
        file.save(path)
        # Limpiar el DataFrame anterior cuando se sube un nuevo archivo
        session.pop('df_summary', None)
        session.pop('df_summary_path', None)
        # Limpiar el archivo JSON si existe
        df_json_path = 'uploads/temp_chunks/df_summary.json'
        if os.path.exists(df_json_path):
            try:
                os.remove(df_json_path)
            except Exception as e:
                print(f"Error removing old df_summary.json: {e}")
    else:
        # Si viene de upload_chunk, la ruta ya está en session['file_path']
        path = session.get('file_path')
        # Si no está en sesión, intenta buscar en mzML_samples/
        if not path and filename:
            path = os.path.join('mzML_samples', filename)
        # Si no hay archivo, error
        if not path or not os.path.exists(path):
            alert = f"Error: Archivo '{path}' no encontrado"
            return render_template('summary.html', error_alert=alert, page='Summary')

    import plotly.io as pio
    import pandas as pd

    try:
        result = get_file_info_extended(path)
        if not result:
            alert = "Error processing file: No data returned."
            return render_template('summary.html', error_alert=alert, page='Summary')
    except Exception as e:
        alert = f"Error processing file: {str(e)}"
        return render_template('summary.html', error_alert=alert, page='Summary')

    # Convertir los valores numpy a tipos nativos para evitar np.float64/np.int32
    def clean_value(val):
        import numpy as np
        if isinstance(val, dict):
            return {k: clean_value(v) for k, v in val.items()}
        elif isinstance(val, (list, tuple)):
            return [clean_value(v) for v in val]
        elif isinstance(val, (np.integer, np.floating)):
            return float(val)
        elif isinstance(val, np.ndarray):
            return val.tolist()
        else:
            return val

    result2 = {k: clean_value(v) for k, v in result.items()}

    # Para 3D spikes y para obtener los datos base
    df_summary = None
    df_json_path = 'uploads/temp_chunks/df_summary.json'

    # Verificar si es una petición AJAX (solo cambio de filtro, no nuevo archivo)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Si es AJAX y tenemos el DataFrame guardado, usarlo
    if is_ajax and 'df_summary_path' in session and os.path.exists(session.get('df_summary_path', '')):
        try:
            df_summary = pd.read_json(session.get('df_summary_path'))
            df_summary['filter_type'] = filter_type
        except Exception as e:
            print(f"Error reading cached df_summary: {e}")
            df_summary = None
    
    # Si no tenemos DataFrame (nuevo archivo o error al leer), cargarlo
    if df_summary is None:
        try: 
            df_summary = load_and_process_data(path)
            df_summary['filter_type'] = filter_type
            # Guardar el DataFrame
            os.makedirs('uploads/temp_chunks', exist_ok=True)
            df_summary.to_json(df_json_path)
            session['df_summary_path'] = df_json_path
            session['df_summary'] = 'loaded'  # Solo un flag, no el JSON completo
        except Exception as e:
            alert = f"Error loading and processing data: {str(e)}"
            return render_template('summary.html', error_alert=alert, page='Summary')

    # Validar que el DataFrame tenga datos válidos
    if df_summary is None or df_summary.empty or df_summary['TIC'].isna().all():
        alert = "Error: No valid data found in the file."
        return render_template('summary.html', error_alert=alert, page='Summary')

    if is_ajax:
        print("AJAX request detected for summary")
        try:
            fig = plot_tic(df_summary=df_summary, mode='3d-spikes', max_points=10000, filter_type=filter_type)
            fig2, _ = plot_tic(df_summary=df_summary, mode='2d', max_points=10000, filter_type=filter_type)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        plot_html = pio.to_html(fig, full_html=False, config={"toImageButtonOptions": {"format": "svg"}, "displaylogo": False})
        plot_html2 = pio.to_html(fig2, full_html=False, config={"toImageButtonOptions": {"format": "svg"}, "displaylogo": False})
        return jsonify({'plot_html': plot_html, 'plot_html2': plot_html2})

    try:
        fig = plot_tic(df_summary=df_summary, mode='3d-spikes', max_points=10000, filter_type=filter_type)
    except Exception as e:
        alert = f"Error generating 3D TIC plot: {str(e)}"
        return render_template('summary.html', error_alert=alert, page='Summary')

    try:
        fig2, _ = plot_tic(df_summary=df_summary, mode='2d', max_points=10000, filter_type=filter_type)
    except Exception as e:
        alert = f"Error generating 2D TIC plot: {str(e)}"
        return render_template('summary.html', error_alert=alert, page='Summary')

    # result plots
    plot_html = pio.to_html(fig, full_html=False, config={"toImageButtonOptions": {"format": "svg"}, "displaylogo": False})
    plot_html2 = pio.to_html(fig2, full_html=False, config={"toImageButtonOptions": {"format": "svg"}, "displaylogo": False})

    # Otherwise, return the full page
    return render_template('summary.html', result=result2, filename=filename, plot_html=plot_html, plot_html2=plot_html2, selected_filter=filter_type, page='Summary')


# Adduct page #############################
@app.route('/adducts')
def adducts():
    if session.get('workflow_status') == 'started':
        if 'adducts' in session.get('current_steps', []) and session.get('step_status') == 'finished':
            session['step_status'] = 'started'
    return render_template('adducts.html', page='Adducts')

# Adducts endpoint/function ####################################
@app.route('/get_files_adducts', methods=['POST'])
def process_adducts():
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), ADDUCTS_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    files = request.files.getlist('filename')
    file_paths = []
    for file in files:
        path = f"{uploads_dir}/{file.filename}"
        file.save(path)
        file_paths.append(path)
        
    for file in file_paths:
        print("Procesando archivo:", file)

    # Llama a get_adduct_files con la lista de archivos
    output_files, output_files2, output_files3 = get_adduct_files(file_paths, ADDUCTS_DIR)

    download_links = []
    download_links2 = []
    download_links3 = []
    for output_file in output_files:
        if output_file and os.path.exists(output_file):
            filename = os.path.basename(output_file)
            download_link = f"/uploads/adducts/{filename}"
            download_links.append(download_link)
        else:
            session['step_status'] = 'started'
            alert = f"Error: adduct files not generated for {output_file}"
            return render_template('adducts.html', download_links=download_links, download_links2=download_links2, download_links3=download_links3, error_alert=alert, page='Adducts')
    for output_file2 in output_files2:
        if output_file2 and os.path.exists(output_file2):
            filename = os.path.basename(output_file2)
            download_link = f"/uploads/adducts/{filename}"
            download_links2.append(download_link)
        else:
            session['step_status'] = 'started'
            alert = f"Error: adduct files not generated for {output_file2}"
            return render_template('adducts.html', download_links=download_links, download_links2=download_links2, download_links3=download_links3, error_alert=alert, page='Adducts')
    for output_file3 in output_files3:
        if output_file3 and os.path.exists(output_file3):
            filename = os.path.basename(output_file3)
            download_link = f"/uploads/adducts/{filename}"
            download_links3.append(download_link)
        else:
            session['step_status'] = 'started'
            alert = f"Error: adduct files not generated for {output_file3}"
            return render_template('adducts.html', download_links=download_links, download_links2=download_links2, download_links3=download_links3, error_alert=alert, page='Adducts')

    # Store generated files in session for workflow tracking
    generated_files = []
    for path in download_links + download_links2 + download_links3:
        generated_files.append({
                "filename": os.path.basename(path),
                "path": path
            })
    workflow_step_finished('adducts', generated_files)
    #advance_workflow_step('adducts')
    return render_template('adducts.html', download_links=download_links, download_links2=download_links2, download_links3=download_links3, page='Adducts')

# Centroiding page ####################################
@app.route('/centroiding')
def centroiding():
    
    if session.get('workflow_status') == 'started':
        if 'centroided' in session.get('current_steps', []) and session.get('step_status') == 'finished':
            session['step_status'] = 'started'
        #session['generated_files'] = []
        
    return render_template('centroiding.html', page='Centroiding')

# Centroiding endpoint/function
@app.route('/get_files_centroiding', methods=['POST'])
def process_centroiding():
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), CENTROIDS_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    
    files = request.files.getlist('filename')
    file_paths = []

    for file in files:
        if file.filename.endswith('.mzML'):
            path = f"{uploads_dir}/{file.filename}"
            if not os.path.exists(path):
                file.save(path)
            file_paths.append(path)
        else:
            alert = 'Please upload only .mzML files for centroiding.'
            session['step_status'] = 'started'
            return render_template('centroiding.html', download_links=None, error_alert=alert, page='Centroiding')

    try:
        output_files = centroid_file(file_paths, CENTROIDS_DIR)
        # Generar links de descarga solo si hay archivos válidos
        download_links = []
        for f in output_files:
            if f and os.path.exists(f):
                filename = os.path.basename(f)
                download_links.append(f"/{CENTROIDS_DIR}/{filename}")
        if not download_links:
            alert = "Error during centroiding: No centroided files generated."
            session['step_status'] = 'started'
            return render_template('centroiding.html', download_links=None, error_alert=alert, page='Centroiding')
        # Store generated files 
        # in session for workflow tracking
        generated_files = []
        for path in download_links:
            generated_files.append({
                "filename": os.path.basename(path),
                "path": path
            })
        workflow_step_finished('centroiding', generated_files)
        #advance_workflow_step('centroiding')
        return render_template('centroiding.html', download_links=download_links, page='Centroiding')
    except Exception as e:
        alert = f"Error during centroiding: {str(e)}"
        session['step_status'] = 'started'
        return render_template('centroiding.html', download_links=None, error_alert=alert, page='Centroiding')

# Accurate mass page ####################################
@app.route('/ami')
def accurate_mass():
    if 'accurate_mass' in session.get('current_steps', []) and session.get('step_status') == 'finished':
        session['step_status'] = 'started'

    return render_template('accurate_mass.html', page='Accurate Mass Search')

# Accurate mass endpoint/function ####################################
@app.route('/get_files_ami', methods=['POST'])
def process_ami():
    # Folder for uploaded files
    uploads_dir = os.path.join(os.getcwd(), ACCURATE_MASS_DIR)
    os.makedirs(uploads_dir, exist_ok=True)
    session['step_status'] = 'started'
    
    consensus_path = request.files.get('filename1')
    consensus_file = os.path.join(uploads_dir, consensus_path.filename)
    consensus_path.save(consensus_file)
    dbmapping = request.files.get('filename2')
    dbmapping_file = os.path.join(uploads_dir, dbmapping.filename)
    dbmapping.save(dbmapping_file)
    dbstruct = request.files.get('filename3')
    dbstruct_file = os.path.join(uploads_dir, dbstruct.filename)
    dbstruct.save(dbstruct_file)
    adducts = request.files.get('filename4')
    adducts_file = os.path.join(uploads_dir, adducts.filename)
    adducts.save(adducts_file)

    result, result2, result3, fig_id = accurate_mass_search(consensus_file, dbmapping_file, dbstruct_file, adducts_file, uploads_dir)
    import plotly.io as pio
    
    if result is not None and result2 is not None and result3 is not None:
        plot_url_ami = pio.to_html(fig_id, full_html=False, include_plotlyjs='cdn')
        download_links = []
        download_links.append(f"{ACCURATE_MASS_DIR}/{os.path.basename(result)}")
        download_links.append(f"{ACCURATE_MASS_DIR}/{os.path.basename(result2)}")
        download_links.append(f"{ACCURATE_MASS_DIR}/{os.path.basename(result3)}")
        # Store generated files in session for workflow tracking
        generated_files = []
        for path in download_links:
            generated_files.append({
                "filename": os.path.basename(path),
                "path": path
            })
        workflow_step_finished('accurate_mass', generated_files)
        # advance_workflow_step('accurate_mass')
        return render_template('accurate_mass.html', result=result, plot_url_ami = plot_url_ami, download_links_search=download_links, page='Accurate Mass Search')
    else:
        
        alert = "Error: Accurate mass search could not be completed. Please check your uploads."
        session['step_status'] = 'started'
        return render_template('accurate_mass.html', error_alert=alert, page='Accurate Mass Search')
# ----------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------------- SERVING UPLOADED FILES --------------------------------------------------
# Accurate mass Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/accurate_mass/<filename>')
def download_accurate_mass(filename):
    return send_from_directory(ACCURATE_MASS_DIR, filename, as_attachment=True)

# NORMALIZE Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/normalize/<filename>')
def download_normalized(filename):
    return send_from_directory(NORMALIZE_DIR, filename, as_attachment=True)

#  ALIGNMENT Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/alignment/<filename>')
def download_alignment(filename):
    return send_from_directory(ALIGNMENT_DIR, filename, as_attachment=True)

#  ADDUCTS Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/adducts/<filename>')
def download_adducts(filename):
    return send_from_directory(ADDUCTS_DIR, filename, as_attachment=True)

# CONSENSUS Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/consensus/<filename>')
def download_consensus(filename):
    uploads_dir = os.path.join(os.getcwd(), CONSENSUS_DIR)
    return send_from_directory(uploads_dir, filename, as_attachment=True)

# SMOOTHING Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/smoothing/<filename>')
def download_smoothing(filename):
    uploads_dir = SMOOTHING_DIR
    return send_from_directory(uploads_dir, filename, as_attachment=True)

# CENTROIDING Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/centroiding/<filename>')
def download_centroid(filename):
    return send_from_directory(CENTROIDS_DIR, filename, as_attachment=True)

# FEATURES Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/features/<filename>')
def download_features(filename):
    return send_from_directory(FEATURES_DIR, filename, as_attachment=True)

#  GNPS Endpoint for serving files from the uploads folder ####################################
@app.route('/uploads/gnps/<filename>')
def download_gnps(filename):
    uploads_dir = os.path.join(os.getcwd(), 'uploads/gnps')
    return send_from_directory(uploads_dir, filename, as_attachment=True)
# ----------------------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------------------

# Backup storage page ####################################
@app.route('/backup')
def backup_storage():
    return render_template('backup_storage.html', page='Backup Storage')


# Backup storage page functions ####################################
@app.route('/show_upload_folders', methods=['GET', 'POST'])
def show_upload_folders():
    upload_folders = {
        'Alignment': ALIGNMENT_DIR,
        'Accurate Mass': ACCURATE_MASS_DIR,
        'Adducts': ADDUCTS_DIR,
        'Centroiding': CENTROIDS_DIR,
        'Consensus': CONSENSUS_DIR,
        'Features': FEATURES_DIR,
        'Normalize': NORMALIZE_DIR,
        'Smoothing': SMOOTHING_DIR,
        'GNPS': GNPS_DIR,
        'Samples': 'mzML_samples',
    }
    folder_contents = {}
    for folder_name, folder_path in upload_folders.items():
        files_info = []
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    created = os.path.getctime(file_path)
                    created_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M:%S')
                    files_info.append({
                        'name': filename,
                        'path': file_path,
                        'size': float(size/1024/1024).__round__(2),
                        'created': created_str
                    })
            folder_contents[folder_name] = files_info
        else:
            folder_contents[folder_name] = []
    return render_template('backup_storage.html', folder_contents=folder_contents, page='Backup Storage')

# Cleaning folders endpoint/function ####################################
@app.route('/clean_folders', methods=['POST'])
def clean_folders():
    data = request.get_json()
    folders = data.get('folders', [])
    # Mapea los nombres a rutas reales
    upload_folders = {
        'Alignment': ALIGNMENT_DIR,
        'Accurate Mass': ACCURATE_MASS_DIR,
        'Adducts': ADDUCTS_DIR,
        'Centroiding': CENTROIDS_DIR,
        'Consensus': CONSENSUS_DIR,
        'Features': FEATURES_DIR,
        'Normalize': NORMALIZE_DIR,
        'Smoothing': SMOOTHING_DIR,
        'GNPS': GNPS_DIR,
        'Samples': 'mzML_samples',
    }
    for folder in folders:
        folder_path = upload_folders.get(folder)
        if folder_path and os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
    return jsonify({'status': 'ok'})

#Upload folders ###########################################################
@app.route('/select_upload_folders', methods=['POST'])
def select_upload_folders():
    upload_folders = {
        'Alignment': ALIGNMENT_DIR,
        'Accurate Mass': ACCURATE_MASS_DIR,
        'Adducts': ADDUCTS_DIR,
        'Centroiding': CENTROIDS_DIR,
        'Consensus': CONSENSUS_DIR,
        'Features': FEATURES_DIR,
        'Normalize': NORMALIZE_DIR,
        'Smoothing': SMOOTHING_DIR,
        'GNPS': GNPS_DIR,
    }
    return upload_folders


# session files testing Endpoint
@app.route('/session_files')
def ver_rutas():
    return str(session.get('file_paths', []))



# Workflow management endpoints/functions ####################################


@app.route('/start_workflow/<int:workflow_id>')
def start_workflow(workflow_id):
    current_steps = []
    workflow0_steps = []
    workflow1_steps = [
        "features",
        "adducts",
        "consensus",
    ]
    workflow2_steps = [
        "centroiding",
        "features",
        "alignment",
        "consensus",
        "accurate_mass",
    ]
    session['workflow_id'] = workflow_id
    session['workflow_status'] = 'started'
    session['step_status'] = 'started'
    session['generated_files'] = {}  
    workflow_status = session['workflow_status']

    if workflow_id == 0:
        current_workflow = "None"
        current_steps = workflow0_steps.copy()
    elif workflow_id == 1:
        current_workflow = "Untargeted Metabolomics Pre-Processing"
        current_steps = workflow1_steps.copy()
    elif workflow_id == 2:
        current_workflow = "Identification by Accurate Mass"
        current_steps = workflow2_steps.copy()
    else:
        current_workflow = None

    session['current_workflow'] = current_workflow
    session['current_steps'] = current_steps

    # Redirect to the first step of the workflow
    if current_steps:
        redirect_link = current_steps[0]
        # session['current_steps'].pop(0)  # Remove the first step as we are going to it now
        
        return redirect(url_for(redirect_link))
    elif current_steps == [] and workflow_id == 0:
        session['workflow_status'] = 'started'
        return render_template('functions_hub.html', page='Functions Hub')

@app.route('/end_workflow')
def end_workflow():
    session.pop('file_paths', None)
    session.pop('file_path', None)
    session.pop('current_workflow', None)
    session.pop('current_steps', None)
    session['workflow_id'] = 0
    session['workflow_status'] = 'finished'
    session['step_status'] = 'finished'
    session['generated_files'] = {}  
    return render_template('index.html', page='Home')



# Get the workflows vars for every page
@app.context_processor
def inject_workflow_vars():
    workflow_id = session.get('workflow_id', 0)
    current_workflow = session.get('current_workflow', None)
    workflow_status = session.get('workflow_status', 'not started')
    current_steps = session.get('current_steps', [])
    step_status = session.get('step_status', 'not started')
    if 'df_summary' in session:
        df_summary = pd.read_json(session.get('df_summary_path'))
    else:
        df_summary = None
    return {
        'workflow_id': workflow_id, 
        'current_workflow': current_workflow, 
        'workflow_status': workflow_status,
        'current_steps': current_steps,
        'step_status': step_status,
        'df_summary': df_summary
    }

def advance_workflow_step(step_name):
    """
    Deletes the current step from the session's current_steps if it matches the provided step_name and the step_status is 'finished'.
    """
    current_steps = session.get('current_steps', [])
    step_status = session.get('step_status', 'not started')
    if current_steps and current_steps[0] == step_name and step_status == 'finished':
        current_steps.pop(0)
        session['current_steps'] = current_steps
        
def workflow_step_finished(step_name=None, generated_files=None):

    if session.get('workflow_status') == 'started':
        if 'generated_files' not in session or not isinstance(session['generated_files'], dict):
            session['generated_files'] = {}
        
        if generated_files:
            # Agrupar archivos por extensión
            for file_info in generated_files:
                filename = file_info.get('filename', '')
                ext = filename.split('.')[-1].lower() if '.' in filename else 'other'
                if ext not in session['generated_files']:
                    session['generated_files'][ext] = []
                session['generated_files'][ext].append(file_info)
            session.modified = True
        session['step_status'] = 'finished'
        
        
@app.route('/next_step')
def next_step():
    current_steps = session.get('current_steps', [])
    if current_steps:
        advance_workflow_step(current_steps[0])
        session['step_status'] = 'started'
    # Redirige al siguiente paso si existe
    if session.get('current_steps'):
        return redirect(url_for(session['current_steps'][0]))
    else:
        return redirect(url_for('index'))
    
# -------------------------------------------------------------------
# SEND FILES ENDPOINT

@app.route('/generated_files/<filename>')
def generated_files(filename):
    workflow_files = session.get('generated_files', [])
    for file in workflow_files:
        if file["filename"] == filename:
            return send_file(file["path"], as_attachment=True)
    return "File not found", 404
# -------------------------------------------------------------------


app.run(host='0.0.0.0', port=5000)