// ========================================
// CONFIGURACIÓN GLOBAL
// ========================================
const CONFIG = {
    API_URL: 'http://127.0.0.1:8000',
    REQUEST_TIMEOUT: 150000, // 2.5 minutos
    PHOTO_STEPS: [
        { id: 'front', label: 'Vista Frontal', instruction: 'Coloque el producto de frente' },
        { id: 'left', label: 'Lateral Izquierdo', instruction: 'Muestre el lado izquierdo del producto' },
        { id: 'right', label: 'Lateral Derecho', instruction: 'Muestre el lado derecho del producto' }
    ]
};

// ========================================
// ESTADO GLOBAL
// ========================================
const state = {
    currentStep: 0,
    photos: [],
    stream: null,
    currentPhotoData: null,
    extractedData: null
};

// ========================================
// INICIALIZACIÓN
// ========================================
document.addEventListener('DOMContentLoaded', init);

function init() {
    setupEventListeners();
    updatePhotoCount();
    updateSessionStatus('Listo');
    console.log('✅ Aplicación inicializada');
}

// ========================================
// GESTIÓN DE CÁMARA
// ========================================
async function initCamera() {
    try {
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            }
        };

        state.stream = await navigator.mediaDevices.getUserMedia(constraints);
        const video = document.getElementById('videoElement');
        video.srcObject = state.stream;
        
        console.log('✅ Cámara iniciada');
    } catch (error) {
        console.error('❌ Error al acceder a la cámara:', error);
        alert('No se puede acceder a la cámara. Verifique los permisos.');
    }
}

function stopCamera() {
    if (state.stream) {
        state.stream.getTracks().forEach(track => track.stop());
        state.stream = null;
        console.log('📷 Cámara detenida');
    }
}

// ========================================
// CAPTURA DE FOTOS
// ========================================
function capturePhoto() {
    const video = document.getElementById('videoElement');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
        state.currentPhotoData = {
            blob: blob,
            url: URL.createObjectURL(blob),
            step: CONFIG.PHOTO_STEPS[state.currentStep]
        };

        console.log('📸 Foto capturada:', state.currentPhotoData.step.label);
        showPreviewModal();
    }, 'image/jpeg', 0.95);
}

function confirmPhoto() {
    // Guardar foto
    state.photos.push(state.currentPhotoData);
    console.log(`✅ Foto confirmada (${state.photos.length}/${CONFIG.PHOTO_STEPS.length})`);
    state.currentPhotoData = null;

    // Avanzar al siguiente paso
    state.currentStep++;

    hidePreviewModal();
    updatePhotosPreview();

    // Mensaje del agente según progreso
    if (state.currentStep < 3) {
        addAgentMessage(
            `<p>✅ Foto ${state.currentStep} de 3 capturada correctamente.</p><p>Por favor, continúa con la siguiente foto: <strong>${CONFIG.PHOTO_STEPS[state.currentStep].label}</strong></p>`,
            [{ text: 'Capturar Siguiente Foto', icon: '📷', onclick: 'continueCapture()', type: 'primary' }]
        );
    } else {
        addAgentMessage(
            `<p>✅ ¡Perfecto! Las 3 fotos han sido capturadas exitosamente.</p><p>Ahora analizaré las imágenes con OCR e IA para extraer toda la información del producto.</p>`,
            [{ text: 'Procesar Producto', icon: '🔍', onclick: 'processFromChat()', type: 'primary' }]
        );
        updateSessionStatus('Fotos listas');
    }
}

function retakePhoto() {
    if (state.currentPhotoData) {
        URL.revokeObjectURL(state.currentPhotoData.url);
    }
    state.currentPhotoData = null;
    hidePreviewModal();
    showCameraModal();
}

function deletePhoto(index) {
    console.log(`🗑️ Eliminando foto ${index}`);
    URL.revokeObjectURL(state.photos[index].url);
    state.photos.splice(index, 1);
    
    // Ajustar paso actual
    state.currentStep = state.photos.length;
    
    updatePhotosPreview();
    
    if (state.photos.length === 0) {
        addAgentMessage(
            '<p>Fotos eliminadas. Puedes comenzar de nuevo cuando estés listo.</p>',
            [{ text: 'Iniciar Cámara', icon: '📷', onclick: 'continueCapture()', type: 'primary' }]
        );
    }
}

// ========================================
// PROCESAMIENTO DEL PRODUCTO
// ========================================
async function processProduct(e) {
    e.preventDefault();
    e.stopPropagation();
    console.log('🛑 Evento cancelado en processProduct');
    
    if (state.photos.length === 0) {
        alert('Debe tomar al menos una foto');
        return;
    }

    console.log(`🔄 Iniciando procesamiento de ${state.photos.length} fotos`);
    
    // Mensaje del agente
    addAgentMessage('<p>⏳ Iniciando análisis de imágenes con OCR e Inteligencia Artificial...</p>');
    
    showProcessingOverlay();

    const formData = new FormData();
    state.photos.forEach((photo, index) => {
        formData.append(`photo_${index}`, photo.blob, `${photo.step.id}.jpg`);
    });

    const controller = new AbortController();
    let timeoutId = null;
    let progressInterval = null;

    try {
        console.log('🧠 [FRONT] Preparando request OCR');
        updateProgress(5, 'Preparando imágenes...');
        await delay(200);

        updateProgress(10, 'Conectando con el servidor...');
        await delay(200);

        console.log('📤 [FRONT] POST →', `${CONFIG.API_URL}/inventory/from-images`);
        console.log('📦 [FRONT] FormData entries:', [...formData.keys()]);

        timeoutId = setTimeout(() => {
            console.warn('⏱️ [FRONT] AbortController ejecutado');
            controller.abort();
        }, CONFIG.REQUEST_TIMEOUT);

        // Progreso visual
        let currentProgress = 15;
        progressInterval = setInterval(() => {
            if (currentProgress < 90) {
                currentProgress += 5;
                updateProgress(currentProgress, 
                    '🔍 Procesando con OCR e IA... Esto puede tardar 30-60 segundos'
                );
            }
        }, 2000);

        updateProgress(15, 'Subiendo imágenes al servidor...');
        console.time('⏳ OCR fetch time');

        const response = await fetch(
            `${CONFIG.API_URL}/inventory/from-images`,
            {
                method: "POST",
                body: formData,
                signal: controller.signal
            }
        );

        console.timeEnd('⏳ OCR fetch time');
        console.log('📥 [FRONT] Response status:', response.status);
        
        clearTimeout(timeoutId);
        clearInterval(progressInterval);

        if (!response.ok) {
            const errText = await response.text();
            console.error('❌ [FRONT] Error response body:', errText);
            throw new Error(`Error del servidor: ${response.status}`);
        }

        updateProgress(92, 'Procesando respuesta del servidor...');
        const data = await response.json();

        console.log("🔎 RAW BACKEND DATA:");
        console.log(JSON.stringify(data, null, 2));
        console.log("🔎 data.product:", data.product);
        console.log("🔎 data.images:", data.images);
        console.log("🔎 data.confidence:", data.confidence);
        console.log("🔎 data.overall_confidence:", data.overall_confidence);

        updateProgress(95, 'Validando información extraída...');
        await delay(300);

        updateProgress(100, 'Completado ✓');
        await delay(500);

        showForm(data);

    } catch (error) {
        console.error('❌ [FRONT] Error capturado:', error);
        console.error('❌ [FRONT] name:', error.name);
        console.error('❌ [FRONT] message:', error.message);

        if (timeoutId) clearTimeout(timeoutId);
        if (progressInterval) clearInterval(progressInterval);

        updateProgress(0, 'Error en el procesamiento');
        hideProcessingOverlay();

        let errorMsg;
        if (error.name === 'AbortError') {
            errorMsg = '⏱️ El procesamiento tardó demasiado tiempo. Por favor, intenta nuevamente.';
        } else {
            errorMsg = error.message || 'Error inesperado al procesar las imágenes';
        }

        addAgentMessage(
            `<p>❌ <strong>Error:</strong> ${errorMsg}</p><p>Por favor, intenta nuevamente o toma nuevas fotos.</p>`,
            [
                { text: 'Intentar de Nuevo', icon: '🔄', onclick: 'processFromChat()', type: 'primary' },
                { text: 'Nuevas Fotos', icon: '📷', onclick: 'resetAll()' }
            ]
        );
    }
}

function updateProgress(percent, status) {
    const progressFill = document.getElementById('progressFill');
    const processingStatus = document.getElementById('processingStatus');
    
    if (progressFill) {
        progressFill.style.width = percent + '%';
    }
    
    if (processingStatus) {
        processingStatus.textContent = status;
    }
    
    console.log(`📊 Progreso: ${percent}% - ${status}`);
}

// ========================================
// FORMULARIO
// ========================================
function showForm(data) {
    console.log('📋 Mostrando formulario con datos:', data);
    
    hideProcessingOverlay();
    
    // Mostrar imagen principal
    const productImageMini = document.getElementById('productImageMini');
    if (state.photos.length > 0) {
        productImageMini.innerHTML = `<img src="${state.photos[0].url}" alt="Producto">`;
    }

    // Mostrar confianza
    const confidenceBadge = document.getElementById('confidenceBadge');
    if (data.confidence !== undefined) {
        const conf = data.confidence;
        let level = 'low';
        let text = 'Baja confianza';
        
        if (conf >= 0.7) {
            level = 'high';
            text = `✓ ${Math.round(conf * 100)}% confianza`;
        } else if (conf >= 0.4) {
            level = 'medium';
            text = `⚠ ${Math.round(conf * 100)}% confianza`;
        } else {
            level = 'low';
            text = `✗ ${Math.round(conf * 100)}% confianza`;
        }
        
        confidenceBadge.className = 'confidence-badge ' + level;
        confidenceBadge.textContent = text;
    }

    // Llenar campos del formulario
    const product = data.product || {};
    
    const fields = {
        'name': product.name || '',
        'brand': product.brand || '',
        'presentation': product.presentation || '',
        'size': product.size || '',
        'barcode': product.barcode || '',
        'batch': product.batch || '',
        'expiry': product.expiry_date || '',
        'price': product.price || ''
    };
    
    // Llenar cada campo
    for (const [fieldId, value] of Object.entries(fields)) {
        const input = document.getElementById(fieldId);
        if (input) {
            input.value = value;
            
            if (value) {
                input.classList.add('filled');
                input.classList.remove('empty');
            } else {
                input.classList.add('empty');
                input.classList.remove('filled');
            }
        }
    }

    // Mostrar advertencias si hay campos faltantes
    const warningBox = document.getElementById('warningBox');
    if (data.missing_fields && data.missing_fields.length > 0) {
        warningBox.innerHTML = `
            <strong>⚠️ Campos incompletos detectados:</strong><br>
            <ul style="margin: 10px 0; padding-left: 20px;">
                ${data.missing_fields.map(field => `<li>${translateFieldName(field)}</li>`).join('')}
            </ul>
            <small>Por favor, complete estos campos manualmente antes de guardar.</small>
        `;
        warningBox.style.display = 'block';
    } else {
        warningBox.style.display = 'none';
    }

    // Mostrar duplicados si existen
    if (data.duplicates && data.duplicates.length > 0) {
        console.log('⚠️ Productos similares encontrados:', data.duplicates);
        
        addAgentMessage(
            `<p>⚠️ <strong>Atención:</strong> Encontré ${data.duplicates.length} producto(s) similar(es) en la base de datos:</p>
            <ul>${data.duplicates.map(d => `<li>${d.name} - ${d.brand} (${Math.round(d.similarity * 100)}% similitud)</li>`).join('')}</ul>
            <p>Verifica que no sea un duplicado antes de guardar.</p>`
        );
    }

    showFormModal();
    
    // Mensaje del agente
    const confidencePercent = Math.round(data.confidence * 100);
    addAgentMessage(
        `<p>✅ <strong>Análisis completado con ${confidencePercent}% de confianza.</strong></p>
        <p>He extraído la información del producto. Por favor, verifica los datos y completa los campos faltantes si es necesario.</p>
        <p>Cuando estés listo, haz clic en <strong>"Guardar Producto"</strong> en el formulario.</p>`
    );
}

async function saveProduct(e) {
    e.preventDefault();
    console.log('💾 Guardando producto...');
    
    const productData = {
        name: document.getElementById('name').value.trim(),
        brand: document.getElementById('brand').value.trim(),
        presentation: document.getElementById('presentation').value.trim() || null,
        size: document.getElementById('size').value.trim(),
        barcode: document.getElementById('barcode').value.trim() || null,
        batch_number: document.getElementById('batch').value.trim() || null,
        expiry_date: document.getElementById('expiry').value || null,
        price: parseFloat(document.getElementById('price').value) || null,
        description: null
    };

    // Validar campos requeridos
    if (!productData.name || !productData.brand || !productData.size) {
        alert('Por favor complete los campos obligatorios:\n- Nombre\n- Marca\n- Tamaño');
        return;
    }

    console.log('📦 Datos a guardar:', productData);

    // Deshabilitar botón mientras guarda
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>⏳</span> Guardando...';

    try {
        const response = await fetch(`${CONFIG.API_URL}/inventory/save`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(productData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al guardar el producto');
        }

        const result = await response.json();
        console.log('✅ Producto guardado exitosamente:', result);
        
        hideFormModal();
        
        addAgentMessage(
            `<p>✅ <strong>¡Producto guardado exitosamente!</strong></p>
            <p><strong>"${result.product?.name || 'Producto'}"</strong> ha sido registrado en la base de datos con ID: <strong>${result.id}</strong></p>
            <p>¿Deseas registrar otro producto?</p>`,
            [{ text: 'Registrar Otro Producto', icon: '➕', onclick: 'resetAll()', type: 'primary' }]
        );
        
        updateSessionStatus('Completado');
        playVoiceConfirmation(result.product?.name || 'Producto');

    } catch (error) {
        console.error('❌ Error al guardar:', error);
        
        addAgentMessage(
            `<p>❌ <strong>Error al guardar:</strong> ${error.message}</p>
             <p>Por favor, verifica los datos e intenta nuevamente.</p>`
        );
        
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// ========================================
// UI - MODALES Y NAVEGACIÓN
// ========================================
function showCameraModal() {
    const modal = document.getElementById('cameraModal');
    modal.classList.add('active');
    updateCameraStep();
}

function hideCameraModal() {
    const modal = document.getElementById('cameraModal');
    modal.classList.remove('active');
    stopCamera();
}

function updateCameraStep() {
    const step = CONFIG.PHOTO_STEPS[state.currentStep];
    if (step) {
        document.getElementById('cameraStepTitle').textContent = `📸 ${step.label}`;
        document.getElementById('cameraStepDesc').textContent = step.instruction;
    }
    
    // Actualizar dots
    document.querySelectorAll('.dot').forEach((dot, index) => {
        dot.classList.remove('active', 'completed');
        if (index < state.currentStep) {
            dot.classList.add('completed');
        } else if (index === state.currentStep) {
            dot.classList.add('active');
        }
    });
}

function showPreviewModal() {
    const previewImage = document.getElementById('previewImage');
    previewImage.src = state.currentPhotoData.url;
    
    const modal = document.getElementById('previewModal');
    modal.classList.add('active');
}

function hidePreviewModal() {
    const modal = document.getElementById('previewModal');
    modal.classList.remove('active');
}

function showFormModal() {
    const modal = document.getElementById('formModal');
    modal.classList.add('active');
}

function hideFormModal() {
    const modal = document.getElementById('formModal');
    modal.classList.remove('active');
}

function showProcessingOverlay() {
    const overlay = document.getElementById('processingOverlay');
    overlay.classList.add('active');
    updateSessionStatus('Procesando...');
}

function hideProcessingOverlay() {
    const overlay = document.getElementById('processingOverlay');
    overlay.classList.remove('active');
}

// ========================================
// UI - CHAT Y MENSAJES
// ========================================
function updatePhotoCount() {
    const photoCount = document.getElementById('photoCount');
    if (photoCount) {
        photoCount.textContent = state.photos.length;
    }
}

function updateSessionStatus(status) {
    const sessionStatus = document.getElementById('sessionStatus');
    if (sessionStatus) {
        sessionStatus.textContent = status;
    }
}

function updatePhotosPreview() {
    const photosPreview = document.getElementById('photosPreview');
    photosPreview.innerHTML = '';
    
    state.photos.forEach((photo, index) => {
        const photoItem = document.createElement('div');
        photoItem.className = 'photo-preview-item';
        photoItem.innerHTML = `
            <img src="${photo.url}" alt="${photo.step.label}">
            <button class="photo-preview-delete" onclick="deletePhoto(${index})">×</button>
            <div class="photo-preview-label">${photo.step.label}</div>
        `;
        photosPreview.appendChild(photoItem);
    });
    
    updatePhotoCount();
}

function addAgentMessage(text, actions = []) {
    const chatMessages = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message agent-message';
    
    let actionsHTML = '';
    if (actions.length > 0) {
        actionsHTML = `<div class="message-actions">
            ${actions.map(action => `
                <button class="action-btn ${action.type || ''}" onclick="${action.onclick}">
                    ${action.icon ? `<span>${action.icon}</span>` : ''}
                    ${action.text}
                </button>
            `).join('')}
        </div>`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text">
                ${text}
            </div>
            ${actionsHTML}
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">
            <div class="message-text">
                <p>${text}</p>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function resetAll() {
    console.log('🔄 Reiniciando aplicación...');
    
    // Limpiar fotos
    state.photos.forEach(photo => URL.revokeObjectURL(photo.url));
    state.photos = [];
    state.currentStep = 0;
    state.extractedData = null;

    // Limpiar preview
    updatePhotosPreview();
    updateSessionStatus('Listo');

    // Cerrar modales
    hideFormModal();
    hideCameraModal();
    hidePreviewModal();
    hideProcessingOverlay();

    // Limpiar chat y mostrar mensaje de bienvenida
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="message agent-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-text">
                    <p>✨ <strong>Nueva sesión iniciada</strong></p>
                    <p>Estoy listo para registrar un nuevo producto. Toma 3 fotos del producto para comenzar:</p>
                    <ul>
                        <li>📸 <strong>Frontal</strong> - Nombre y marca</li>
                        <li>📸 <strong>Lateral izquierdo</strong> - Ingredientes</li>
                        <li>📸 <strong>Lateral derecho</strong> - Información nutricional</li>
                    </ul>
                </div>
                <div class="message-actions">
                    <button class="action-btn primary" onclick="continueCapture()">
                        <span>📷</span>
                        Iniciar Cámara
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ========================================
// EVENT LISTENERS
// ========================================
function setupEventListeners() {
    // Botón iniciar cámara (mensaje de bienvenida)
    document.getElementById('startCameraBtn').addEventListener('click', async () => {
        await initCamera();
        showCameraModal();
        updateSessionStatus('Capturando fotos...');
    });
    
    // Botón toggle cámara (inferior)
    document.getElementById('cameraToggleBtn').addEventListener('click', async () => {
        if (state.photos.length < 3) {
            await initCamera();
            showCameraModal();
            updateSessionStatus('Capturando fotos...');
        } else {
            processProduct(new Event('click'));
        }
    });
    
    // Captura de foto
    document.getElementById('captureBtn').addEventListener('click', () => {
        capturePhoto();
        hideCameraModal();
    });
    
    // Confirmar foto
    document.getElementById('confirmPhotoBtn').addEventListener('click', confirmPhoto);
    
    // Reintentar foto
    document.getElementById('retakeBtn').addEventListener('click', retakePhoto);
    
    // Cerrar cámara
    document.getElementById('closeCameraBtn').addEventListener('click', hideCameraModal);
    
    // Cerrar preview
    document.getElementById('closePreviewBtn').addEventListener('click', hidePreviewModal);
    
    // Cerrar formulario
    document.getElementById('closeFormBtn').addEventListener('click', () => {
        hideFormModal();
        addAgentMessage(
            '<p>Formulario cerrado. Los datos no se guardaron.</p>',
            [{ text: 'Volver a Intentar', icon: '📝', onclick: 'showFormModal()', type: 'primary' }]
        );
    });
    
    // Cancelar formulario
    document.getElementById('cancelFormBtn').addEventListener('click', () => {
        hideFormModal();
        addAgentMessage(
            '<p>Operación cancelada. ¿Deseas comenzar de nuevo?</p>',
            [{ text: 'Nueva Captura', icon: '📷', onclick: 'resetAll()', type: 'primary' }]
        );
    });
    
    // Nueva sesión
    document.getElementById('newSessionBtn').addEventListener('click', resetAll);
    
    // Guardar producto
    document.getElementById('productForm').addEventListener('submit', saveProduct);
}

// ========================================
// FUNCIONES AUXILIARES GLOBALES
// ========================================
window.continueCapture = async function() {
    await initCamera();
    showCameraModal();
    updateCameraStep();
    updateSessionStatus('Capturando fotos...');
};

window.processFromChat = function() {
    processProduct(new Event('click'));
};

window.deletePhoto = deletePhoto;

// ========================================
// UTILIDADES
// ========================================
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function translateFieldName(field) {
    const translations = {
        'name': 'Nombre del producto',
        'brand': 'Marca',
        'size': 'Tamaño',
        'presentation': 'Presentación',
        'barcode': 'Código de barras',
        'batch': 'Lote',
        'expiry_date': 'Fecha de vencimiento',
        'price': 'Precio'
    };
    return translations[field] || field;
}

async function playVoiceConfirmation(productName) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/inventory/voice/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_name: productName })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const audioUrl = URL.createObjectURL(blob);
            const audio = document.getElementById('confirmationAudio');
            audio.src = audioUrl;
            
            // Reproducir audio
            await audio.play();
            
            console.log('🎤 Audio de confirmación reproducido');
        } else {
            console.warn('⚠️ Servicio de voz no disponible');
        }
    } catch (error) {
        console.log('⚠️ Voz no disponible:', error);
    }
}