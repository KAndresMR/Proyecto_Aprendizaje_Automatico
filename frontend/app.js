// URLs
const API_PREDICT = "https://stock-api-1025275139192.us-central1.run.app/predict";
const API_UPDATE  = "https://stock-api-1025275139192.us-central1.run.app/update-dataset";
const API_SUMMARY = "https://stock-api-1025275139192.us-central1.run.app/llm-summary";

// Sidebar navigation
const tabs = document.querySelectorAll(".side-btn");
const panels = document.querySelectorAll(".panel");

tabs.forEach(btn => {
  btn.addEventListener("click", () => {
    const target = btn.getAttribute("data-target");
    if (!target) return;

    tabs.forEach(b => b.classList.remove("active"));
    panels.forEach(p => p.classList.remove("active"));

    btn.classList.add("active");
    document.querySelector(target).classList.add("active");
  });
});

// ======= PREDICCIÓN =================
const btn = document.getElementById("btnPredict");
const statusDiv = document.getElementById("status");
const resultsDiv = document.getElementById("results-container");
const llmOut = document.getElementById("llm-output");

btn.addEventListener("click", async () => {

  const date = document.getElementById("fecha").value;
  const productId = document.getElementById("product_id").value;
  const allProducts = document.getElementById("all_products").checked;

  if (!date) {
    statusDiv.textContent = "Selecciona una fecha.";
    return;
  }

  if (!allProducts && !productId) {
    statusDiv.textContent = "Selecciona un producto o marca 'Todos'.";
    return;
  }

  const payload = {
    date: date,
    all_products: allProducts
  };

  if (!allProducts) {
    payload.product_id = productId;
  }

  btn.disabled = true;
  statusDiv.textContent = "Consultando servicio...";

  let data = null;

  try {
    const resp = await fetch(API_PREDICT, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      statusDiv.textContent = "Error: " + resp.status;
      resultsDiv.innerHTML = await resp.text();
      btn.disabled = false;
      return;
    }

    data = await resp.json();

    let html = `
      <table>
        <tr>
          <th>Producto</th>
          <th>Fecha</th>
          <th>Predicción</th>
          <th>Alerta</th>
        </tr>
    `;

    data.forEach(row => {
      html += `
        <tr>
          <td>${row.product_id}</td>
          <td>${row.date}</td>
          <td>${row.pred_quantity_sold.toFixed(2)}</td>
          <td>
            <span class="badge ${row.alert === "CRITICO" ? "critico" : "ok"}">${row.alert}</span>
          </td>
        </tr>
      `;
    });

    html += "</table>";
    resultsDiv.innerHTML = html;

    statusDiv.textContent = "OK";

  } catch (err) {
    statusDiv.textContent = "Error llamando al servicio";
  }

  // LLM SUMMARY
  try {
    const respLLM = await fetch(API_SUMMARY, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ predictions: data })
    });

    if (!respLLM.ok) {
      llmOut.innerHTML = "No se pudo generar el resumen.";
    } else {
      const dataLLM = await respLLM.json();
      llmOut.innerHTML = marked.parse(dataLLM.summary);
    }

  } catch (e) {
    llmOut.innerHTML = "Error llamando al LLM.";
  }

  btn.disabled = false;
});


// =========== UPDATE MODEL ====================
const btnUpdate = document.getElementById("btnUpdate");
const updateStatus = document.getElementById("update-status");
const fileInput = document.getElementById("csvFile");

btnUpdate.addEventListener("click", async () => {
  const file = fileInput.files[0];

  if (!file) {
    updateStatus.textContent = "Selecciona un archivo CSV primero.";
    updateStatus.className = "status error";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  btnUpdate.disabled = true;
  updateStatus.textContent = "Actualizando modelo...";

  try {
    const resp = await fetch(API_UPDATE, {
      method: "POST",
      body: formData
    });

    const data = await resp.json();

    if (!resp.ok) {
      updateStatus.textContent = "Error: " + (data.detail || resp.status);
      updateStatus.className = "status error";
      return;
    }

    updateStatus.textContent = "Actualización completada";
    updateStatus.className = "status ok";

  } catch (err) {
    updateStatus.textContent = "Error llamando al servicio.";
    updateStatus.className = "status error";
  }

  btnUpdate.disabled = false;
});
``
