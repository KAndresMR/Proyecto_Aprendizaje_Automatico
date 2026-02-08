// ========================================
// CONFIGURACIÓN GLOBAL
// ========================================
const CONFIG = {
    API_URL: 'http://127.0.0.1:8000',
    REQUEST_TIMEOUT: 120000, // 2 minutos (120 segundos)
    PHOTO_STEPS: [
        { id: 'front', label: 'Vista Frontal', instruction: 'Coloque el producto de frente' },
        { id: 'left', label: 'Lateral Izquierdo', instruction: 'Muestre el lado izquierdo del producto' },
        { id: 'right', label: 'Lateral Derecho', instruction: 'Muestre el lado derecho del producto' },
        { id: 'back', label: 'Vista Trasera (Opcional)', instruction: 'Muestre la parte trasera con la información nutricional' }
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

async function init() {
    await initCamera();
    setupEventListeners();
    updateStepIndicator();
    console.log('✅ Aplicación inicializada');
}

// ========================================
// GESTIÓN DE CÁMARA
// ========================================
async function initCamera() {
    try {
        const constraints = {
            video: {
                facingMode: 'environment', // Cámara trasera en móviles
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

    // Ajustar canvas al tamaño del video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Capturar frame actual
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convertir a blob
    canvas.toBlob((blob) => {
        state.currentPhotoData = {
            blob: blob,
            url: URL.createObjectURL(blob),
            step: CONFIG.PHOTO_STEPS[state.currentStep]
        };

        console.log('📸 Foto capturada:', state.currentPhotoData.step.label);
        showPreview();
    }, 'image/jpeg', 0.95);
}

function showPreview() {
    const previewImage = document.getElementById('previewImage');
    previewImage.src = state.currentPhotoData.url;

    switchScreen('previewScreen');
}

function confirmPhoto() {
    // Guardar foto
    state.photos.push(state.currentPhotoData);
    console.log(`✅ Foto confirmada (${state.photos.length}/${CONFIG.PHOTO_STEPS.length})`);
    
    state.currentPhotoData = null;

    // Avanzar al siguiente paso
    state.currentStep++;

    // Si es la última foto obligatoria o el usuario quiere terminar
    if (state.currentStep >= 3) { // 3 primeras fotos obligatorias
        showGallery();
    } else {
        updateStepIndicator();
        switchScreen('cameraScreen');
    }
}

function retakePhoto() {
    if (state.currentPhotoData) {
        URL.revokeObjectURL(state.currentPhotoData.url);
    }
    state.currentPhotoData = null;
    switchScreen('cameraScreen');
}

// ========================================
// GALERÍA
// ========================================
function showGallery() {
    stopCamera();
    
    const photoGrid = document.getElementById('photoGrid');
    photoGrid.innerHTML = '';

    state.photos.forEach((photo, index) => {
        const photoItem = document.createElement('div');
        photoItem.className = 'photo-item';
        photoItem.innerHTML = `
            <img src="${photo.url}" alt="${photo.step.label}">
            <div class="photo-label">${photo.step.label}</div>
            <button class="photo-delete" onclick="deletePhoto(${index})">×</button>
        `;
        photoGrid.appendChild(photoItem);
    });

    console.log(`📸 Galería mostrada con ${state.photos.length} fotos`);
    switchScreen('galleryScreen');
}

function deletePhoto(index) {
    console.log(`🗑️ Eliminando foto ${index}`);
    URL.revokeObjectURL(state.photos[index].url);
    state.photos.splice(index, 1);
    
    if (state.photos.length === 0) {
        state.currentStep = 0;
        initCamera();
        updateStepIndicator();
        switchScreen('cameraScreen');
    } else {
        showGallery();
    }
}

async function addMorePhotos() {
    state.currentStep = state.photos.length;
    await initCamera();
    updateStepIndicator();
    switchScreen('cameraScreen');
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
    switchScreen('processingScreen');

    const formData = new FormData();
    state.photos.forEach((photo, index) => {
        formData.append(`photo_${index}`, photo.blob, `${photo.step.id}.jpg`);
    });

    // 🔑 UN SOLO CONTROL

    const controller = new AbortController();
    let timeoutId = null;
    let progressInterval= null;

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
        }, CONFIG.REQUEST_TIMEOUT); // 120000

        // 📊 Progreso visual
        let currentProgress = 15;
        progressInterval = setInterval(() => {
            if (currentProgress < 90) {
                currentProgress += 5;
                updateProgress(currentProgress, 
                    '🔍 Procesando OCR... Esto puede tardar 1-2 minutos'
                );
            }
        }, 3000);

        updateProgress(15, 'Subiendo imágenes...');
        console.time('⏳ OCR fetch time');

        console.log('🧨 [FRONT] Antes del fetch');

        const response = await fetch(
            `${CONFIG.API_URL}/inventory/from-images`,
            {
                method: "POST",
                body: formData,
                signal: controller.signal
            }
        );

        console.log('🧨 [FRONT] Después del fetch (NO deberías perder esto)');

        console.timeEnd('⏳ OCR fetch time');

        console.log('📥 [FRONT] Response status:', response.status);
        
        // ❗ IMPORTANTE: limpiar timers SOLO después de response
        clearTimeout(timeoutId);
        clearInterval(progressInterval);

        if (!response.ok) {
            const errText = await response.text();
            console.error('❌ [FRONT] Error response body:', errText);
            throw new Error(`Backend error ${response.status}`);
        }

        updateProgress(92, 'Procesando respuesta del servidor...');
        const data = await response.json();

        console.log("BACKEND OCR RESULT:", data);

        updateProgress(95, 'Validando información...');
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

        let errorMsg;
        if (error.name === 'AbortError') {
            errorMsg = '⏱️ El OCR tardó demasiado tiempo.\nEspere hasta 2 minutos.';
        } else {
            errorMsg = error.message || 'Error inesperado';
        }

        alert('Error al procesar imágenes:\n\n' + errorMsg);
        showGallery();
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
            
            // Marcar visualmente campos completados
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
    }

    // Cambiar a la pantalla del formulario
    switchScreen('formScreen');
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
        
        showSuccess(result);

    } catch (error) {
        console.error('❌ Error al guardar:', error);
        alert('Error al guardar el producto:\n\n' + error.message);
        
        // Rehabilitar botón
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

function showSuccess(result) {
    const successMessage = document.getElementById('successMessage');
    successMessage.textContent = `"${result.product?.name || 'Producto'}" registrado correctamente con ID: ${result.id}`;
    
    switchScreen('successScreen');
}

// ========================================
// NAVEGACIÓN
// ========================================
function switchScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
    console.log(`🔄 Pantalla cambiada a: ${screenId}`);
}

function updateStepIndicator() {
    const step = CONFIG.PHOTO_STEPS[state.currentStep];
    if (step) {
        document.getElementById('stepIndicator').textContent = 
            `Foto ${state.currentStep + 1} de 4: ${step.label}`;
        document.querySelector('.instructions p').textContent = step.instruction;
    }
}

function resetAll() {
    console.log('🔄 Reiniciando aplicación...');
    
    // Limpiar fotos
    state.photos.forEach(photo => URL.revokeObjectURL(photo.url));
    state.photos = [];
    state.currentStep = 0;
    state.extractedData = null;

    // Reiniciar cámara
    initCamera();
    updateStepIndicator();
    switchScreen('cameraScreen');
}

// ========================================
// EVENT LISTENERS
// ========================================
function setupEventListeners() {
    document.getElementById('captureBtn').addEventListener('click', capturePhoto);
    document.getElementById('retakeBtn').addEventListener('click', retakePhoto);
    document.getElementById('confirmPhotoBtn').addEventListener('click', confirmPhoto);
    document.getElementById('addMoreBtn').addEventListener('click', addMorePhotos);
    document.getElementById('processBtn').addEventListener('click', processProduct);
    document.getElementById('productForm').addEventListener('submit', saveProduct);
    document.getElementById('cancelFormBtn').addEventListener('click', resetAll);
    document.getElementById('newProductBtn').addEventListener('click', resetAll);
    
    console.log('✅ Event listeners configurados');
}

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

// Exportar funciones globales para onclick
window.deletePhoto = deletePhoto;