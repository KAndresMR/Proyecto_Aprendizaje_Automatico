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
    console.log('✅ Aplicación inicializada con chat conversacional');
}

// ========================================
// GESTIÓN DE CHAT CONVERSACIONAL
// ========================================
async function handleChatSubmit(e) {
    e.preventDefault();
    
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    
    if (!query) return;
    
    // Limpiar input
    input.value = '';
    
    // Agregar mensaje del usuario
    addUserMessage(query);
    
    // Procesar consulta
    await processQuery(query);
}

async function processQuery(query) {
    const lowerQuery = query.toLowerCase();
    
    // Mensaje de "pensando"
    const thinkingMsg = addAgentMessage('<p>🤔 Analizando tu consulta...</p>');
    
    try {
        // ====================================
        // DETECTAR TIPO DE CONSULTA
        // ====================================
        
        // 1. Contar productos
        if (lowerQuery.includes('cuántos') || lowerQuery.includes('total') || lowerQuery.includes('cantidad')) {
            await handleCountQuery(thinkingMsg);
        }
        
        // 2. Buscar producto específico
        else if (lowerQuery.includes('busca') || lowerQuery.includes('muestra') || lowerQuery.includes('encuentra') || lowerQuery.includes('dame')) {
            await handleSearchQuery(query, thinkingMsg);
        }
        
        // 3. Productos por vencer
        else if (lowerQuery.includes('vence') || lowerQuery.includes('expir') || lowerQuery.includes('caducidad')) {
            await handleExpiryQuery(thinkingMsg);
        }
        
        // 4. Últimos productos
        else if (lowerQuery.includes('últim') || lowerQuery.includes('recient') || lowerQuery.includes('nuevo')) {
            await handleRecentQuery(thinkingMsg);
        }
        
        // 5. Productos por marca
        else if (lowerQuery.includes('marca') || lowerQuery.includes('de gloria') || lowerQuery.includes('de nestle')) {
            await handleBrandQuery(query, thinkingMsg);
        }
        
        // 6. Stock bajo
        else if (lowerQuery.includes('stock') || lowerQuery.includes('inventario bajo') || lowerQuery.includes('pocos')) {
            await handleLowStockQuery(thinkingMsg);
        }
        
        // 7. Ayuda
        else if (lowerQuery.includes('ayuda') || lowerQuery.includes('help') || lowerQuery.includes('qué puedes')) {
            showHelpMessage(thinkingMsg);
        }
        
        // 8. No entendido
        else {
            showUnknownQueryMessage(thinkingMsg);
        }
        
    } catch (error) {
        console.error('Error procesando consulta:', error);
        updateAgentMessage(thinkingMsg, `
            <p>❌ Error al procesar tu consulta.</p>
            <p>Por favor, intenta de nuevo o usa el botón de ayuda.</p>
        `);
    }
}

// ========================================
// HANDLERS DE CONSULTAS ESPECÍFICAS
// ========================================

async function handleCountQuery(messageElement) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/inventory/products`);
        
        if (!response.ok) {
            throw new Error('Error al consultar productos');
        }
        
        const products = await response.json();
        const totalProducts = products.length;
        
        updateAgentMessage(messageElement, `
            <p>📊 <strong>Información de Inventario</strong></p>
            <p>Actualmente hay <strong>${totalProducts}</strong> producto(s) registrado(s) en el sistema.</p>
        `);
        
    } catch (error) {
        updateAgentMessage(messageElement, `
            <p>❌ No pude obtener el conteo de productos.</p>
            <p>Error: ${error.message}</p>
        `);
    }
}

async function handleSearchQuery(query, messageElement) {
    try {
        // Extraer el término de búsqueda
        const searchTerms = query.toLowerCase()
            .replace(/busca|muestra|encuentra|dame|el|la|los|las|producto|productos|de/g, '')
            .trim();
        
        if (!searchTerms) {
            updateAgentMessage(messageElement, `
                <p>⚠️ No especificaste qué producto buscar.</p>
                <p>Ejemplo: "Busca Coca Cola" o "Muéstrame productos de Gloria"</p>
            `);
            return;
        }
        
        const response = await fetch(`${CONFIG.API_URL}/inventory/products`);
        
        if (!response.ok) {
            throw new Error('Error al buscar productos');
        }
        
        const products = await response.json();
        
        // Filtrar productos que coincidan
        const matches = products.filter(p => 
            p.name.toLowerCase().includes(searchTerms) ||
            p.brand.toLowerCase().includes(searchTerms)
        );
        
        if (matches.length === 0) {
            updateAgentMessage(messageElement, `
                <p>🔍 No encontré productos con "<strong>${searchTerms}</strong>"</p>
                <p>Intenta con otro nombre o marca.</p>
            `);
            return;
        }
        
        // Mostrar resultados
        let resultsHTML = `
            <p>🔍 Encontré <strong>${matches.length}</strong> producto(s):</p>
            <div style="margin-top: 12px;">
        `;
        
        matches.slice(0, 5).forEach(product => {
            resultsHTML += `
                <div style="background: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #2d2d2d;">
                    <strong>${product.name}</strong><br>
                    <small style="color: #9ca3af;">Marca: ${product.brand} | Tamaño: ${product.size}</small><br>
                    ${product.image_front ? `<img src="${CONFIG.API_URL}${product.image_front}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 4px; margin-top: 8px;">` : ''}
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        
        if (matches.length > 5) {
            resultsHTML += `<p><small>Mostrando los primeros 5 de ${matches.length} resultados</small></p>`;
        }
        
        updateAgentMessage(messageElement, resultsHTML);
        
    } catch (error) {
        updateAgentMessage(messageElement, `
            <p>❌ Error al buscar productos.</p>
            <p>${error.message}</p>
        `);
    }
}

async function handleExpiryQuery(messageElement) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/inventory/products`);
        
        if (!response.ok) {
            throw new Error('Error al consultar productos');
        }
        
        const products = await response.json();
        const today = new Date();
        const thirtyDaysFromNow = new Date(today.getTime() + (30 * 24 * 60 * 60 * 1000));
        
        // Filtrar productos que vencen en 30 días
        const expiringProducts = products.filter(p => {
            if (!p.expiry_date) return false;
            const expiryDate = new Date(p.expiry_date);
            return expiryDate <= thirtyDaysFromNow && expiryDate >= today;
        });
        
        if (expiringProducts.length === 0) {
            updateAgentMessage(messageElement, `
                <p>✅ No hay productos próximos a vencer en los siguientes 30 días.</p>
            `);
            return;
        }
        
        let resultsHTML = `
            <p>⚠️ <strong>${expiringProducts.length}</strong> producto(s) vencen pronto:</p>
            <div style="margin-top: 12px;">
        `;
        
        expiringProducts.forEach(product => {
            const daysUntilExpiry = Math.floor((new Date(product.expiry_date) - today) / (24 * 60 * 60 * 1000));
            const urgencyColor = daysUntilExpiry < 7 ? '#dc2626' : '#d97706';
            
            resultsHTML += `
                <div style="background: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid ${urgencyColor};">
                    <strong>${product.name}</strong><br>
                    <small style="color: #9ca3af;">Marca: ${product.brand}</small><br>
                    <small style="color: ${urgencyColor}; font-weight: 600;">⏰ Vence en ${daysUntilExpiry} día(s) - ${product.expiry_date}</small>
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        updateAgentMessage(messageElement, resultsHTML);
        
    } catch (error) {
        updateAgentMessage(messageElement, `
            <p>❌ Error al consultar productos por vencer.</p>
            <p>${error.message}</p>
        `);
    }
}

async function handleRecentQuery(messageElement) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/inventory/products`);
        
        if (!response.ok) {
            throw new Error('Error al consultar productos');
        }
        
        const products = await response.json();
        
        // Ordenar por ID descendente (más recientes primero)
        const recentProducts = products
            .sort((a, b) => b.id - a.id)
            .slice(0, 5);
        
        if (recentProducts.length === 0) {
            updateAgentMessage(messageElement, `
                <p>ℹ️ No hay productos registrados aún.</p>
            `);
            return;
        }
        
        let resultsHTML = `
            <p>📦 <strong>Últimos ${recentProducts.length} productos registrados:</strong></p>
            <div style="margin-top: 12px;">
        `;
        
        recentProducts.forEach(product => {
            resultsHTML += `
                <div style="background: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #2d2d2d;">
                    <strong>${product.name}</strong><br>
                    <small style="color: #9ca3af;">Marca: ${product.brand} | Tamaño: ${product.size}</small><br>
                    ${product.image_front ? `<img src="${CONFIG.API_URL}${product.image_front}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 4px; margin-top: 8px;">` : ''}
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        updateAgentMessage(messageElement, resultsHTML);
        
    } catch (error) {
        updateAgentMessage(messageElement, `
            <p>❌ Error al consultar productos recientes.</p>
            <p>${error.message}</p>
        `);
    }
}

async function handleBrandQuery(query, messageElement) {
    try {
        // Extraer marca
        const brandMatch = query.match(/de\s+([a-záéíóúñ\s]+)/i);
        const brand = brandMatch ? brandMatch[1].trim() : '';
        
        if (!brand) {
            updateAgentMessage(messageElement, `
                <p>⚠️ No especificaste la marca.</p>
                <p>Ejemplo: "Muéstrame productos de Gloria"</p>
            `);
            return;
        }
        
        const response = await fetch(`${CONFIG.API_URL}/inventory/products`);
        
        if (!response.ok) {
            throw new Error('Error al buscar productos');
        }
        
        const products = await response.json();
        
        // Filtrar por marca
        const brandProducts = products.filter(p => 
            p.brand.toLowerCase().includes(brand.toLowerCase())
        );
        
        if (brandProducts.length === 0) {
            updateAgentMessage(messageElement, `
                <p>🔍 No encontré productos de la marca "<strong>${brand}</strong>"</p>
            `);
            return;
        }
        
        let resultsHTML = `
            <p>🏷️ Productos de <strong>${brand}</strong> (${brandProducts.length}):</p>
            <div style="margin-top: 12px;">
        `;
        
        brandProducts.slice(0, 5).forEach(product => {
            resultsHTML += `
                <div style="background: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #2d2d2d;">
                    <strong>${product.name}</strong><br>
                    <small style="color: #9ca3af;">Tamaño: ${product.size}</small>
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        
        if (brandProducts.length > 5) {
            resultsHTML += `<p><small>Mostrando los primeros 5 de ${brandProducts.length} resultados</small></p>`;
        }
        
        updateAgentMessage(messageElement, resultsHTML);
        
    } catch (error) {
        updateAgentMessage(messageElement, `
            <p>❌ Error al buscar por marca.</p>
            <p>${error.message}</p>
        `);
    }
}

async function handleLowStockQuery(messageElement) {
    updateAgentMessage(messageElement, `
        <p>ℹ️ La funcionalidad de stock bajo está en desarrollo.</p>
        <p>Próximamente podrás ver productos con inventario limitado.</p>
    `);
}

function showHelpMessage(messageElement) {
    updateAgentMessage(messageElement, `
        <p>💡 <strong>¿Qué puedo hacer por ti?</strong></p>
        <p>Puedo ayudarte con:</p>
        <ul>
            <li>📊 <strong>Contar productos:</strong> "¿Cuántos productos hay?"</li>
            <li>🔍 <strong>Buscar productos:</strong> "Busca Coca Cola" o "Muéstrame productos de Gloria"</li>
            <li>📦 <strong>Ver últimos registros:</strong> "Muéstrame los últimos productos"</li>
            <li>⚠️ <strong>Productos por vencer:</strong> "¿Qué productos están por vencer?"</li>
            <li>📸 <strong>Registrar nuevo producto:</strong> Usa el botón de cámara</li>
        </ul>
        <p><strong>Tip:</strong> También puedes usar los botones de acciones rápidas en la barra lateral.</p>
    `, [
        { text: '📷 Registrar Producto', icon: '📷', onclick: 'continueCapture()', type: 'primary' }
    ]);
}

function showUnknownQueryMessage(messageElement) {
    updateAgentMessage(messageElement, `
        <p>🤔 No entendí tu consulta.</p>
        <p>Intenta con algo como:</p>
        <ul>
            <li>"¿Cuántos productos hay?"</li>
            <li>"Busca Coca Cola"</li>
            <li>"Muéstrame productos de Gloria"</li>
            <li>"¿Qué productos vencen pronto?"</li>
        </ul>
    `, [
        { text: '💡 Ver Ayuda', icon: '💡', onclick: 'sendQuickQuery("ayuda")', type: 'primary' }
    ]);
}

// ========================================
// UTILIDADES DE MENSAJES
// ========================================
function updateAgentMessage(messageElement, newContent, actions = []) {
    const contentDiv = messageElement.querySelector('.message-text');
    if (contentDiv) {
        contentDiv.innerHTML = newContent;
    }
    
    // Actualizar acciones si las hay
    if (actions.length > 0) {
        let existingActions = messageElement.querySelector('.message-actions');
        if (!existingActions) {
            existingActions = document.createElement('div');
            existingActions.className = 'message-actions';
            messageElement.querySelector('.message-content').appendChild(existingActions);
        }
        
        existingActions.innerHTML = actions.map(action => `
            <button class="action-btn ${action.type || ''}" onclick="${action.onclick}">
                ${action.icon ? `<span>${action.icon}</span>` : ''}
                ${action.text}
            </button>
        `).join('');
    }
}

window.sendQuickQuery = function(query) {
    const input = document.getElementById('chatInput');
    input.value = query;
    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
};

// ========================================
// GESTIÓN DE CÁMARA (ORIGINAL)
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

function updateCameraStep() {
    const step = CONFIG.PHOTO_STEPS[state.currentStep];
    if (!step) return;
    
    document.getElementById('cameraStepTitle').textContent = `📸 ${step.label}`;
    document.getElementById('cameraStepDesc').textContent = step.instruction;
    
    // Actualizar puntos de progreso
    document.querySelectorAll('.progress-dots .dot').forEach((dot, index) => {
        if (index === state.currentStep) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });
}

// ========================================
// CAPTURA DE FOTOS (ORIGINAL)
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
    state.photos.push(state.currentPhotoData);
    console.log(`✅ Foto confirmada (${state.photos.length}/${CONFIG.PHOTO_STEPS.length})`);
    state.currentPhotoData = null;

    state.currentStep++;

    hidePreviewModal();
    updatePhotosPreview();

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
// PROCESAMIENTO DEL PRODUCTO (ORIGINAL)
// ========================================
async function processProduct(e) {
    e.preventDefault();
    e.stopPropagation();
    
    if (state.photos.length === 0) {
        alert('Debe tomar al menos una foto');
        return;
    }

    console.log(`🔄 Iniciando procesamiento de ${state.photos.length} fotos`);
    
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
        updateProgress(5, 'Preparando imágenes...');
        await delay(200);

        updateProgress(10, 'Conectando con el servidor...');
        await delay(200);

        timeoutId = setTimeout(() => {
            controller.abort();
        }, CONFIG.REQUEST_TIMEOUT);

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

        const response = await fetch(
            `${CONFIG.API_URL}/inventory/from-images`,
            {
                method: "POST",
                body: formData,
                signal: controller.signal
            }
        );

        clearTimeout(timeoutId);
        clearInterval(progressInterval);

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Error del servidor: ${response.status}`);
        }

        updateProgress(92, 'Procesando respuesta del servidor...');
        const data = await response.json();

        updateProgress(95, 'Validando información extraída...');
        await delay(300);

        updateProgress(100, 'Completado ✓');
        await delay(500);

        showForm(data);

    } catch (error) {
        clearTimeout(timeoutId);
        clearInterval(progressInterval);
        
        console.error('❌ Error en procesamiento:', error);
        
        hideProcessingOverlay();
        
        addAgentMessage(
            `<p>❌ Error al procesar las imágenes: ${error.message}</p>`,
            [{ text: 'Reintentar', icon: '🔄', onclick: 'processFromChat()', type: 'primary' }]
        );
    }
}

// ========================================
// MOSTRAR FORMULARIO (ORIGINAL)
// ========================================
function showForm(data) {
    hideProcessingOverlay();
    
    state.extractedData = data;
    
    const product = data.product || {};
    const confidence = data.confidence || 0;
    
    document.getElementById('name').value = product.name || '';
    document.getElementById('brand').value = product.brand || '';
    document.getElementById('size').value = product.size || '';
    document.getElementById('presentation').value = product.presentation || '';
    document.getElementById('barcode').value = product.barcode || '';
    document.getElementById('batch').value = product.batch || '';
    document.getElementById('expiry').value = product.expiry_date || '';
    document.getElementById('price').value = product.price || '';
    
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
    
    const productImageMini = document.getElementById('productImageMini');
    if (state.photos.length > 0) {
        productImageMini.innerHTML = `<img src="${state.photos[0].url}" alt="Producto">`;
    }
    
    const warningBox = document.getElementById('warningBox');
    const missingFields = data.missing_fields || [];
    
    if (missingFields.length > 0) {
        warningBox.style.display = 'block';
        warningBox.innerHTML = `
            <strong>⚠️ Campos sin detectar:</strong><br>
            ${missingFields.map(f => translateFieldName(f)).join(', ')}
        `;
    } else {
        warningBox.style.display = 'none';
    }
    
    showFormModal();
    
    addAgentMessage(
        '<p>✅ Información extraída correctamente. Por favor, verifica los datos y guarda el producto.</p>'
    );
}

// ========================================
// GUARDAR PRODUCTO (ORIGINAL)
// ========================================
async function saveProduct(e) {
    e.preventDefault();
    
    const productData = {
        name: document.getElementById('name').value,
        brand: document.getElementById('brand').value,
        size: document.getElementById('size').value,
        presentation: document.getElementById('presentation').value,
        barcode: document.getElementById('barcode').value,
        batch: document.getElementById('batch').value,
        expiry_date: document.getElementById('expiry').value,
        price: parseFloat(document.getElementById('price').value) || null
    };
    
    if (!productData.name || !productData.brand || !productData.size) {
        alert('Por favor, complete los campos obligatorios: Nombre, Marca y Tamaño');
        return;
    }
    
    console.log('💾 Guardando producto:', productData);
    
    try {
        hideFormModal();
        showProcessingOverlay();
        updateProgress(30, 'Guardando producto...');
        
        await delay(1000);
        
        updateProgress(100, 'Producto guardado ✓');
        await delay(500);
        
        hideProcessingOverlay();
        
        addAgentMessage(
            `<p>✅ ¡Producto guardado exitosamente!</p>
             <p><strong>${productData.name}</strong> de <strong>${productData.brand}</strong> ha sido registrado en el inventario.</p>`,
            [{ text: 'Registrar Otro Producto', icon: '📷', onclick: 'resetAll()', type: 'primary' }]
        );
        
        await playVoiceConfirmation(productData.name);
        
        updateSessionStatus('Completado');
        
    } catch (error) {
        console.error('Error guardando producto:', error);
        hideProcessingOverlay();
        alert('Error al guardar el producto. Por favor, intente nuevamente.');
    }
}

// ========================================
// GESTIÓN DE MODALES (ORIGINAL)
// ========================================
function showCameraModal() {
    document.getElementById('cameraModal').classList.add('active');
    updateCameraStep();
}

function hideCameraModal() {
    document.getElementById('cameraModal').classList.remove('active');
    stopCamera();
}

function showPreviewModal() {
    const modal = document.getElementById('previewModal');
    const previewImage = document.getElementById('previewImage');
    previewImage.src = state.currentPhotoData.url;
    modal.classList.add('active');
}

function hidePreviewModal() {
    document.getElementById('previewModal').classList.remove('active');
}

function showFormModal() {
    document.getElementById('formModal').classList.add('active');
}

function hideFormModal() {
    document.getElementById('formModal').classList.remove('active');
}

function showProcessingOverlay() {
    document.getElementById('processingOverlay').classList.add('active');
}

function hideProcessingOverlay() {
    document.getElementById('processingOverlay').classList.remove('active');
}

function updateProgress(percent, message) {
    document.getElementById('progressFill').style.width = `${percent}%`;
    document.getElementById('processingStatus').textContent = message;
}

// ========================================
// ACTUALIZACIÓN DE UI (ORIGINAL)
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
    
    return messageDiv;
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
    
    state.photos.forEach(photo => URL.revokeObjectURL(photo.url));
    state.photos = [];
    state.currentStep = 0;
    state.extractedData = null;

    updatePhotosPreview();
    updateSessionStatus('Listo');

    hideFormModal();
    hideCameraModal();
    hidePreviewModal();
    hideProcessingOverlay();

    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="message agent-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-text">
                    <p>✨ <strong>Nueva sesión iniciada</strong></p>
                    <p>Estoy listo para registrar un nuevo producto o responder tus consultas.</p>
                </div>
                <div class="message-actions">
                    <button class="action-btn primary" onclick="continueCapture()">
                        <span>📷</span>
                        Registrar Producto
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
    // Chat form
    document.getElementById('chatForm').addEventListener('submit', handleChatSubmit);
    
    // Botón iniciar cámara
    document.getElementById('startCameraBtn').addEventListener('click', async () => {
        await initCamera();
        showCameraModal();
        updateSessionStatus('Capturando fotos...');
    });
    
    // Botón toggle cámara
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
    
    // Cerrar modales
    document.getElementById('closeCameraBtn').addEventListener('click', hideCameraModal);
    document.getElementById('closePreviewBtn').addEventListener('click', hidePreviewModal);
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
window.showFormModal = showFormModal;

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
        'price': 'Precio',
        'category': 'Categoría'
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
            await audio.play();
            console.log('🎤 Audio de confirmación reproducido');
        }
    } catch (error) {
        console.log('⚠️ Voz no disponible:', error);
    }
}
