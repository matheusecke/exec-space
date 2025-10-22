/**
 * Frontend JavaScript para ExecSpace
 */

let currentEnvironmentId = null;
let logsRefreshInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  refreshEnvironments();

  const form = document.getElementById("createEnvironmentForm");
  form.addEventListener("submit", handleCreateEnvironment);

  setInterval(refreshEnvironments, 5000);
});

async function handleCreateEnvironment(event) {
  event.preventDefault();

  const formData = new FormData(event.target);
  const data = {
    name: formData.get("name"),
    cpu_limit: parseFloat(formData.get("cpu_limit")),
    memory_mb: parseInt(formData.get("memory_mb")),
    io_weight: parseInt(formData.get("io_weight")),
    script_content: formData.get("script_content"),
  };

  const submitButton = event.target.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = "Criando...";

  try {
    const response = await fetch("/api/environments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Erro ao criar ambiente");
    }

    const result = await response.json();

    showSuccessMessage("Ambiente criado com sucesso");

    event.target.reset();

    await refreshEnvironments();
  } catch (error) {
    console.error("Erro:", error);
    showErrorMessage(error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Criar e Executar";
  }
}

async function refreshEnvironments() {
  try {
    const response = await fetch("/api/environments");

    if (!response.ok) {
      throw new Error("Erro ao carregar ambientes");
    }

    const environments = await response.json();
    renderEnvironments(environments);
  } catch (error) {
    console.error("Erro:", error);
    const listElement = document.getElementById("environmentsList");
    listElement.innerHTML = `<p class="error-message">Erro ao carregar ambientes: ${error.message}</p>`;
  }
}

function renderEnvironments(environments) {
  const listElement = document.getElementById("environmentsList");

  if (environments.length === 0) {
    listElement.innerHTML = `
      <div class="empty-state">
        <h3>Nenhum ambiente criado</h3>
        <p>Crie seu primeiro ambiente usando o formulário acima.</p>
      </div>
    `;
    return;
  }

  const html = `
    <div class="environments-grid">
      ${environments.map((env) => renderEnvironmentCard(env)).join("")}
    </div>
  `;

  listElement.innerHTML = html;
}

function renderEnvironmentCard(env) {
  const statusClass = `status-${env.status.toLowerCase()}`;
  const statusText =
    {
      RUNNING: "Executando",
      EXITED: "Finalizado",
      ERROR: "Erro",
    }[env.status] || env.status;

  const createdDate = new Date(env.created_at).toLocaleString("pt-BR");

  return `
    <div class="environment-card">
      <div class="environment-header">
        <h3>${escapeHtml(env.name)}</h3>
        <span class="status-badge ${statusClass}">${statusText}</span>
      </div>
      
      <div class="environment-info">
        <div class="info-row">
          <span class="info-label">CPU:</span>
          <span class="info-value">${env.cpu_limit} cores</span>
        </div>
        <div class="info-row">
          <span class="info-label">Memória:</span>
          <span class="info-value">${env.memory_mb} MB</span>
        </div>
        <div class="info-row">
          <span class="info-label">I/O:</span>
          <span class="info-value">${env.io_weight}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Criado:</span>
          <span class="info-value">${createdDate}</span>
        </div>
      </div>
      
      <div class="environment-actions">
        <button class="btn" onclick="showLogs('${env.id}')">
          Ver Logs
        </button>
        ${
          env.status === "RUNNING"
            ? `
          <button class="btn btn-secondary" onclick="stopEnvironment('${env.id}')">
            Parar
          </button>
        `
            : ""
        }
        <button class="btn btn-danger" onclick="confirmDelete('${
          env.id
        }', '${escapeHtml(env.name)}')">
          Remover
        </button>
      </div>
    </div>
  `;
}

async function showLogs(environmentId) {
  currentEnvironmentId = environmentId;

  const modal = document.getElementById("logsModal");
  const logsContent = document.getElementById("logsContent");

  modal.classList.add("show");
  logsContent.innerHTML = "<p>Carregando logs...</p>";
  logsContent.classList.add("empty");

  await loadLogs(environmentId);

  if (logsRefreshInterval) {
    clearInterval(logsRefreshInterval);
  }
  logsRefreshInterval = setInterval(() => loadLogs(environmentId), 2000);
}

async function loadLogs(environmentId) {
  try {
    const response = await fetch(`/api/environments/${environmentId}/logs`);

    if (!response.ok) {
      throw new Error("Erro ao carregar logs");
    }

    const data = await response.json();
    const logsContent = document.getElementById("logsContent");

    if (data.logs && data.logs.trim() !== "") {
      logsContent.textContent = data.logs;
      logsContent.classList.remove("empty");
    } else {
      logsContent.innerHTML = '<p class="empty">Nenhum log disponível</p>';
      logsContent.classList.add("empty");
    }

    logsContent.scrollTop = logsContent.scrollHeight;
  } catch (error) {
    console.error("Erro ao carregar logs:", error);
    const logsContent = document.getElementById("logsContent");
    logsContent.innerHTML = `<p class="error-message">Erro: ${error.message}</p>`;
  }
}

function refreshLogs() {
  if (currentEnvironmentId) {
    loadLogs(currentEnvironmentId);
  }
}

function closeLogsModal() {
  const modal = document.getElementById("logsModal");
  modal.classList.remove("show");
  currentEnvironmentId = null;

  if (logsRefreshInterval) {
    clearInterval(logsRefreshInterval);
    logsRefreshInterval = null;
  }
}

async function stopEnvironment(environmentId) {
  try {
    const response = await fetch(`/api/environments/${environmentId}/stop`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Erro ao parar ambiente");
    }

    showSuccessMessage("Ambiente parado com sucesso");
    await refreshEnvironments();
  } catch (error) {
    console.error("Erro:", error);
    showErrorMessage(error.message);
  }
}

function confirmDelete(environmentId, environmentName) {
  const modal = document.getElementById("confirmModal");
  const message = document.getElementById("confirmMessage");
  const confirmButton = document.getElementById("confirmButton");

  message.textContent = `Tem certeza que deseja remover o ambiente "${environmentName}"? Esta ação não pode ser desfeita.`;

  confirmButton.onclick = () => {
    deleteEnvironment(environmentId);
    closeConfirmModal();
  };

  modal.classList.add("show");
}

function closeConfirmModal() {
  const modal = document.getElementById("confirmModal");
  modal.classList.remove("show");
}

async function deleteEnvironment(environmentId) {
  try {
    const response = await fetch(`/api/environments/${environmentId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Erro ao remover ambiente");
    }

    showSuccessMessage("Ambiente removido com sucesso");
    await refreshEnvironments();
  } catch (error) {
    console.error("Erro:", error);
    showErrorMessage(error.message);
  }
}

function showSuccessMessage(message) {
  const container = document.getElementById("notificationsContainer");
  const messageDiv = document.createElement("div");
  messageDiv.className = "success-message";
  messageDiv.textContent = message;

  container.appendChild(messageDiv);

  setTimeout(() => {
    messageDiv.remove();
  }, 5000);
}

function showErrorMessage(message) {
  const container = document.getElementById("notificationsContainer");
  const messageDiv = document.createElement("div");
  messageDiv.className = "error-message";
  messageDiv.textContent = message;

  container.appendChild(messageDiv);

  setTimeout(() => {
    messageDiv.remove();
  }, 5000);
}

function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

window.onclick = function (event) {
  const logsModal = document.getElementById("logsModal");
  const confirmModal = document.getElementById("confirmModal");

  if (event.target === logsModal) {
    closeLogsModal();
  }
  if (event.target === confirmModal) {
    closeConfirmModal();
  }
};
