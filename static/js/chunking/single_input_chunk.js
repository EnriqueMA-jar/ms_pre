// Chunks upload with progress bar
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('inputGroupFile04');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('uploadProgress');
    const progressPercent = document.getElementById('progressPercent');

    if (form) {
        form.addEventListener('submit', function(e) {
            const files = fileInput.files;
            if (!files.length) return;
            e.preventDefault();

            // --- NUEVO: calcular progreso global por bytes ---
            let totalBytes = 0;
            for (let i = 0; i < files.length; i++) totalBytes += files[i].size;
            let uploadedBytes = 0;

            let fileIndex = 0;
            progressContainer.style.display = 'block';
            progressBar.style.width = '0%';
            progressPercent.textContent = '0%';

            // helper: generar id simple único por archivo
            function generateUploadId(file) {
                return `${Date.now()}-${Math.floor(Math.random() * 1e9)}-${file.name.replace(/\s+/g, '_')}`;
            }

            // helper: fetch con timeout usando AbortController
            function fetchWithTimeout(url, options = {}, timeout = 30000) {
                const controller = new AbortController();
                options.signal = controller.signal;
                const timer = setTimeout(() => controller.abort(), timeout);
                return fetch(url, options).finally(() => clearTimeout(timer));
            }

            function uploadFile(file, onComplete, onError) {
                const chunkSize = 2 * 1024 * 1024; // 2MB por chunk
                const totalChunks = Math.ceil(file.size / chunkSize);
                let currentChunk = 0;
                const uploadId = generateUploadId(file);

                function uploadNextChunk() {
                    const start = currentChunk * chunkSize;
                    const end = Math.min(start + chunkSize, file.size);
                    const chunk = file.slice(start, end);
                    const formData = new FormData();
                    formData.append('chunk', chunk);
                    formData.append('filename', file.name);
                    formData.append('upload_id', uploadId);
                    formData.append('chunk_index', currentChunk);
                    formData.append('total_chunks', totalChunks);
                    formData.append('target_dir', window.targetDir || 'mzML_samples');

                    const maxRetries = 3;
                    let attempt = 0;

                    function sendChunk() {
                        attempt++;
                        fetchWithTimeout('/upload_chunk', {
                            method: 'POST',
                            body: formData
                        }, 30000)
                        .then(response => {
                            if (!response.ok) {
                                return response.text().then(text => {
                                    let msg = `Server returned ${response.status}`;
                                    try {
                                        const j = JSON.parse(text || '{}');
                                        msg = j.error || JSON.stringify(j) || msg;
                                    } catch {}
                                    return Promise.reject(new Error(msg));
                                });
                            }
                            return response.text().then(txt => {
                                try { return JSON.parse(txt || '{}'); } catch { return {}; }
                            });
                        })
                        .then(data => {
                            // actualizar progreso global por bytes reales
                            uploadedBytes += chunk.size;
                            const percent = Math.floor((uploadedBytes / totalBytes) * 100);
                            progressBar.style.width = percent + '%';
                            progressPercent.textContent = percent + '%';

                            currentChunk++;
                            if ((data && data.status === 'complete') || currentChunk >= totalChunks) {
                                // asegurar 100% si acabó este archivo y es el último
                                if (uploadedBytes === totalBytes) {
                                    progressBar.style.width = '100%';
                                    progressPercent.textContent = '100%';

                                    if (typeof window.showProcessingSpinner === 'function') {
                                        window.showProcessingSpinner();
                                    }
                                    setTimeout(() => {
                                        form.submit();
                                    }, 300);
                                }
                                onComplete();
                            } else {
                                uploadNextChunk();
                            }
                        })
                        .catch(err => {
                            console.error(`Chunk ${currentChunk} upload error (attempt ${attempt}):`, err);
                            if (attempt < maxRetries) {
                                const baseDelay = 500 * Math.pow(2, attempt - 1);
                                const jitter = Math.floor(Math.random() * 200);
                                const delay = baseDelay + jitter;
                                setTimeout(sendChunk, delay);
                            } else {
                                // error definitivo: informar y detener subida
                                onError(err);
                            }
                        });
                    }
                    sendChunk();
                }
                uploadNextChunk();
            }

            function uploadAllFiles() {
                if (fileIndex >= files.length) {
                    // Todos los archivos subidos, enviar el form
                    if (typeof window.showProcessingSpinner === 'function') {
                        window.showProcessingSpinner();
                    }
                    for (let i = 0; i < files.length; i++) {
                        const hidden = document.createElement('input');
                        hidden.type = 'hidden';
                        hidden.name = 'filename';
                        hidden.value = files[i].name;
                        form.appendChild(hidden);
                    }
                    form.submit();
                    return;
                }
                uploadFile(files[fileIndex], function() {
                    fileIndex++;
                    uploadAllFiles();
                }, function(err) {
                    alert('Error al subir "' + files[fileIndex].name + '": ' + (err.message || JSON.stringify(err)));
                    console.error('Upload aborted for file:', files[fileIndex].name, err);
                    // detener cualquier otra subida: no avanzar fileIndex
                });
            }
            uploadAllFiles();
        });
    }
});