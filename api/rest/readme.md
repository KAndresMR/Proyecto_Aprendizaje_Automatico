# Parte 2

## Register
Registra un producto en el motor SIFT y lo almacena en la base de datos interna.

URL  
/register [POST]

### Input (multipart/form-data)

image (File, requerido) – Imagen del producto  
name (String, opcional) – Nombre del producto (default: "Unknown")  
threshold (Float, opcional) – Umbral de contraste SIFT (default: 0.04)  
mask (File, opcional) – Máscara binaria

### Output

200 OK  
Producto registrado correctamente

---

## Preview Keypoints
Previsualización de los puntos clave SIFT.

URL  
/preview_keypoints [POST]

### Input (multipart/form-data)

image (File, requerido)  
threshold (Float, opcional)  
mask (File, opcional)

### Output

200 OK
keypoint_image (base64)  
count (int)

---

## Predict
Identificación de producto.

URL  
/predict [POST]

### Input (multipart/form-data)

image (File, requerido)

### Output

200 OK
label  
matches  
probability

---

## Versions
Listado de versiones del modelo.

URL  
/mlflow/versions [GET]

### Output

200 OK
run_id  -- id de la version
date   -- fecha de registro
product_count  -- cantidad de productos registrados

---

## Restore
Restauración de una versión previa del modelo.

URL  
/mlflow/restore [POST]

### Input (application/json)

run_id

### Output

200 OK
message  -- mensaje de confirmacion
count    -- cantidad de productos registrados



## De la parte 1 lo que les pedí fué

- métodos para obtener productos de la base de datos, por el identificador según ProductStockSchema
- Imágenes de productos (5 productos, 3 imágenes por producto).
- Guardar datos extraídos de las imágenes (OCR, etiquetas, unidades y cantidades).
- Normalizar las unidades (convertir todo a gramos) y almacenar solo el valor convertido. y hacer transformaciones a otras unidades




