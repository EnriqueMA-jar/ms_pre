#Esta herramienta aplica un filtro de suavizado temporal a los espectros de masas para reducir el ruido y mejorar la calidad de los datos. A diferencia de otros métodos que combinan múltiples espectros en uno solo, el suavizado espectral preserva todos los espectros originales, pero para cada uno calcula un promedio ponderado con sus espectros vecinos en tiempo de retención. El método gaussiano asigna mayor peso a los espectros más cercanos temporalmente (ventana gaussiana), mientras que el método tophat utiliza un promedio simple donde todos los vecinos tienen el mismo peso (ventana rectangular). Este proceso es especialmente útil para datos LC-MS ruidosos, ya que cancela fluctuaciones aleatorias y refuerza señales consistentes, manteniendo la separación cromatográfica original. El resultado es un conjunto de espectros con el mismo número de scans pero con picos más definidos y menor ruido de fondo, lo que facilita la detección posterior de features y la identificación de metabolitos.


#¿Para qué sirve?
#Beneficios:
#Reduce ruido aleatorio - señales espurias se cancelan
#Suaviza fluctuaciones - picos se ven más estables
#Mejora relación señal/ruido - señales reales se refuerzan
#Mantiene número de espectros - no pierdes resolución temporal


#########################################
# Spectral Denoising

###############################################

import pyopenms as oms

# Ruta del archivo de entrada
input_file = "/home/labi/Documents/Aquismon/Centroide/EO_01A_Centroide.mzML"

# Ruta de salida para el archivo promediado
output_file = "/home/labi/Documents/Aquismon/EO_01A_averaged.mzML"

# Cargar datos MS
exp = oms.MSExperiment()
oms.MzMLFile().load(input_file, exp)
spectra = exp.getSpectra()

# Contar espectros MS1 antes del promediado
spectra_ms1 = [s for s in spectra if s.getMSLevel() == 1]
print(f"📊 Espectros MS1 antes del promediado: {len(spectra_ms1)}")

# Promediar espectros con método gaussiano
merger = oms.SpectraMerger()
merger.average(exp, "gaussian")
spectraAveraged = exp.getSpectra()

# Contar espectros MS1 después del promediado
spectraAveraged_ms1 = [s for s in spectraAveraged if s.getMSLevel() == 1]
print(f"📊 Espectros MS1 después del promediado: {len(spectraAveraged_ms1)}")

# Guardar datos promediados
oms.MzMLFile().store(output_file, exp)
print(f"💾 Archivo guardado: {output_file}")
