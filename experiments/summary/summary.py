from pyopenms import MSExperiment, MzMLFile

def get_file_info(file_path):
    # Load the .mzML file
    exp = MSExperiment()
    MzMLFile().load(file_path, exp)
    
    
    # Basic metaData
    num_spectra = exp.getNrSpectra()
    num_chroms = exp.getNrChromatograms()
    rt_range = (exp.getMinRT()/60, exp.getMaxRT()/60) # Convert to minutes
    mz_range = (exp.getMinMZ(), exp.getMaxMZ())
    
    # count MS levels (MS1, MS2)
    ms1 = 0
    ms2 = 0
    for spec in exp:
        if spec.getMSLevel() ==1:
            ms1 += 1
        elif spec.getMSLevel() == 2:
            ms2 += 1
            
    # if theres an instrument, get its info 
    instrument = "unavailable"
    if exp.getInstrument() is not None:
        instrument = exp.getInstrument().getName() # if theres a name, get it
        
    # print summary
    # print(f"File: {file_path}")
    # print(f"- Number of Spectra: {num_spectra}")
    # print(f"- Number of Chromatograms: {num_chroms}")
    # print(f"- MS Levels (MS1: {ms1}, MS2: {ms2})")
    # print(f"- Retention Time Range (min): [{rt_range[0]:.2f},{rt_range[1]:.2f}]")
    # print(f"- m/z Range: [{mz_range[0]:.2f},{mz_range[1]:.2f}]")
    # print(f"- Instument: {instrument}")
    
    
    # create a dictionary with the info
    summary = []
    summary.append(f"File: {file_path}")
    summary.append(f"- Number of Spectra: {num_spectra}")
    summary.append(f"- Number of Chromatograms: {num_chroms}")
    summary.append(f"- MS Levels (MS1: {ms1}, MS2: {ms2})")
    summary.append(f"- Retention Time Range (min): [{rt_range[0]:.2f},{rt_range[1]:.2f}]")
    summary.append(f"- m/z Range: [{mz_range[0]:.2f},{mz_range[1]:.2f}]")
    summary.append(f"- Instrument: {instrument}")
    
    

    return "\n".join(summary)
