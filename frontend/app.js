// ================================
// CONFIG
// ================================
const CONFIG = {
  API_BASE: "https://stock-api-1025275139192.us-central1.run.app",
  ENDPOINTS: {
    predict: "/predict",
    update: "/update-dataset",
    summary: "/llm-summary"
  }
};

// ================================
// API CLIENT
// ================================
const api = {
  async postJSON(path, body) {
    const resp = await fetch(CONFIG.API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (!resp.ok) throw await parseError(resp);
    return resp.json();
  },

  async postForm(path, formData) {
    const resp = await fetch(CONFIG.API_BASE + path, {
      method: "POST",
      body: formData
    });

    const data = await resp.json();
    if (!resp.ok) throw data;
    return data;
  }
};

async function parseError(resp) {
  try {
    return await resp.json();
  } catch {
    return { detail: "Error inesperado del servidor" };
  }
}

// ================================
// UI HELPERS
// ================================
const ui = {
  setText(id, text, type = "") {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className = `status ${type}`;
  },

  renderTable(rows) {
    if (!rows || rows.length === 0) {
      document.getElementById("results-container").innerHTML = "Sin resultados.";
      return;
    }

    const html = `
      <table>
        <tr>
          <th>Producto</th>
          <th>Fecha</th>
          <th>Predicción</th>
          <th>Estado</th>
        </tr>
        ${rows.map(r => `
          <tr>
            <td>${r.product_id}</td>
            <td>${r.date}</td>
            <td>${Number(r.pred_quantity_sold).toFixed(2)}</td>
            <td>
              <span class="badge ${r.alert === "CRITICO" ? "critico" : "ok"}">
                ${r.alert}
              </span>
            </td>
          </tr>
        `).join("")}
      </table>
    `;
    document.getElementById("results-container").innerHTML = html;
  },

  renderLLM(text) {
    document.getElementById("llm-output").innerHTML =
      text ? marked.parse(text) : "Sin conclusiones.";
  }
};

// ================================
// NAV
// ================================
document.querySelectorAll(".side-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.target;
    if (!target) return;

    document.querySelectorAll(".side-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));

    btn.classList.add("active");
    document.querySelector(target).classList.add("active");
  });
});

// ================================
// PREDICT
// ================================
document.getElementById("btnPredict").addEventListener("click", async () => {
  const date = document.getElementById("fecha").value;
  const productId = document.getElementById("product_id").value;
  const allProducts = document.getElementById("all_products").checked;

  if (!date) return ui.setText("status", "Selecciona una fecha.", "error");
  if (!allProducts && !productId)
    return ui.setText("status", "Selecciona producto o todos.", "error");

  const payload = {
    date,
    all_products: allProducts,
    ...(allProducts ? {} : { product_id: productId })
  };

  const btn = document.getElementById("btnPredict");
  btn.disabled = true;
  ui.setText("status", "Consultando modelo...");

  let predictions = null;

  try {
    predictions = await api.postJSON(CONFIG.ENDPOINTS.predict, payload);
    ui.renderTable(predictions);
    ui.setText("status", "OK", "ok");
  } catch (e) {
    ui.setText("status", e.detail || "Error en predicción", "error");
    btn.disabled = false;
    return;
  }

  // LLM
  try {
    const llm = await api.postJSON(CONFIG.ENDPOINTS.summary, {
      predictions
    });
    ui.renderLLM(llm.summary);
  } catch {
    ui.renderLLM("No se pudo generar el resumen.");
  }

  btn.disabled = false;
});

// ================================
// UPDATE DATASET
// ================================
document.getElementById("btnUpdate").addEventListener("click", async () => {
  const file = document.getElementById("csvFile").files[0];
  if (!file) return ui.setText("update-status", "Selecciona un archivo", "error");

  const form = new FormData();
  form.append("file", file);

  const btn = document.getElementById("btnUpdate");
  btn.disabled = true;
  ui.setText("update-status", "Actualizando...");

  try {
    const data = await api.postForm(CONFIG.ENDPOINTS.update, form);
    ui.setText(
      "update-status",
      `Actualizado. Registros añadidos: ${data.rows_added}`,
      "ok"
    );
  } catch (e) {
    ui.setText("update-status", e.detail || "Error actualizando", "error");
  }

  btn.disabled = false;
});