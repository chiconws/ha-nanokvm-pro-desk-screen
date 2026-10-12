const SECURITY_URL =
  "https://github.com/chiconws/ha-nanokvm-pro-desk-screen/blob/main/SECURITY.md";

class NanoKVMProDeskScreenPanel extends HTMLElement {
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first && this._selected) {
      this._startRefresh();
    }
  }

  set panel(panel) {
    this._panel = panel;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  disconnectedCallback() {
    this._stopRefresh();
  }

  _render() {
    if (!this.isConnected || !this._panel) {
      return;
    }

    const entries = this._panel.config?.entries || [];
    const screenSize =
      this._screenSize || localStorage.getItem("nanokvmDeskScreenSize") || "2";
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    const currentIndex = Number(this._selectedIndex || 0);
    const selected = entries[Math.min(currentIndex, Math.max(entries.length - 1, 0))];
    const agentReachable = Boolean(selected?.agent_installed);
    const setupRequired = selected ? !selected.agent_configured || !agentReachable : false;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
        }
        .page {
          box-sizing: border-box;
          display: grid;
          grid-template-rows: auto minmax(0, 1fr);
          gap: 12px;
          height: 100%;
          padding: 16px;
        }
        .toolbar {
          display: flex;
          align-items: center;
          gap: 12px;
          min-height: 40px;
          flex-wrap: wrap;
        }
        .title {
          font-size: 20px;
          font-weight: 500;
          margin-right: auto;
        }
        select,
        input {
          box-sizing: border-box;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          padding: 8px;
        }
        .content {
          display: grid;
          align-content: center;
          justify-items: center;
          gap: 16px;
          min-height: 0;
          width: 100%;
        }
        .setup-callout {
          box-sizing: border-box;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 16px;
          align-items: center;
          width: min(760px, 100%);
          padding: 16px;
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
          border: 1px solid color-mix(in srgb, var(--primary-color) 42%, var(--divider-color));
          border-radius: 4px;
        }
        .setup-title {
          font-size: 16px;
          font-weight: 600;
          margin-bottom: 4px;
        }
        .setup-text {
          color: var(--secondary-text-color);
          line-height: 1.4;
        }
        .viewer {
          display: grid;
          grid-template-columns: minmax(0, max-content) 120px;
          gap: 12px;
          align-items: center;
          min-height: 0;
        }
        .viewer[data-screen-size="fit"] {
          grid-template-columns: minmax(0, 1fr) 120px;
          width: 100%;
          max-width: 1200px;
        }
        .screen-column {
          display: grid;
          gap: 6px;
          justify-items: end;
          width: var(--screen-width, 640px);
          max-width: 100%;
        }
        .viewer[data-screen-size="fit"] .screen-column {
          width: 100%;
        }
        .screen {
          display: grid;
          place-items: center;
          position: relative;
          min-width: 0;
          min-height: 0;
          width: 100%;
          aspect-ratio: 320 / 172;
          background: #000;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          overflow: hidden;
          touch-action: none;
        }
        .viewer[data-screen-size="fit"] .screen {
          width: 100%;
        }
        .screen-status {
          position: absolute;
          inset: 0;
          display: grid;
          place-items: center;
          padding: 16px;
          color: #fff;
          background: rgba(0, 0, 0, 0.72);
          text-align: center;
        }
        .screen-status[hidden] {
          display: none;
        }
        .screen-badge {
          box-sizing: border-box;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          padding: 4px 8px;
          color: #fff;
          background: rgba(0, 0, 0, 0.72);
          border: 1px solid rgba(255, 255, 255, 0.18);
          border-radius: 999px;
          font-size: 12px;
          line-height: 1.2;
        }
        img {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: contain;
          image-rendering: pixelated;
          user-select: none;
          -webkit-user-drag: none;
        }
        .controls {
          display: grid;
          gap: 8px;
          align-content: center;
        }
        button {
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          min-height: 48px;
          cursor: pointer;
          padding: 0 12px;
        }
        button:hover {
          border-color: var(--primary-color);
        }
        button:disabled {
          cursor: progress;
          opacity: 0.6;
        }
        .toolbar button {
          min-height: 36px;
        }
        .primary-agent {
          background: var(--primary-color);
          border-color: var(--primary-color);
          color: #fff;
          font-weight: 600;
        }
        .primary-agent:hover {
          filter: brightness(1.08);
        }
        .primary-agent.large {
          min-width: 144px;
        }
        .message {
          display: grid;
          place-items: center;
          height: 100%;
          color: var(--secondary-text-color);
        }
        .modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 10;
          display: grid;
          place-items: center;
          padding: 16px;
          background: rgba(0, 0, 0, 0.52);
        }
        .modal {
          box-sizing: border-box;
          width: min(640px, 100%);
          max-height: 100%;
          overflow: auto;
          padding: 20px;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.32));
        }
        .modal h2 {
          margin: 0 0 12px;
          font-size: 20px;
          font-weight: 500;
        }
        .security-note {
          margin-bottom: 16px;
          padding: 12px;
          color: var(--primary-text-color);
          background: rgba(255, 152, 0, 0.12);
          border: 1px solid rgba(255, 152, 0, 0.45);
          border-radius: 4px;
          line-height: 1.45;
        }
        .security-note a {
          color: var(--primary-color);
        }
        .agent-form {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }
        .field {
          display: grid;
          gap: 6px;
        }
        .field.full {
          grid-column: 1 / -1;
        }
        label {
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        .agent-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 16px;
        }
        .agent-actions button {
          min-height: 40px;
        }
        .agent-message {
          margin-top: 12px;
          min-height: 20px;
          color: var(--secondary-text-color);
          line-height: 1.4;
        }
        @media (max-width: 720px) {
          .viewer {
            grid-template-columns: 1fr;
          }
          .controls {
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }
          .setup-callout {
            grid-template-columns: 1fr;
            justify-items: start;
          }
          .agent-form {
            grid-template-columns: 1fr;
          }
        }
      </style>
      <div class="page">
        <div class="toolbar">
          <div class="title">NanoKVM Pro Desk Screen</div>
          ${
            selected
              ? `<button
                  type="button"
                  data-open-agent
                  class="${setupRequired ? "primary-agent" : ""}"
                >${selected.agent_configured ? "Manage agent" : "Set up agent"}</button>
                <select id="screen-size" title="Screen size" aria-label="Screen size">
                  <option value="1" ${screenSize === "1" ? "selected" : ""}>1x</option>
                  <option value="1.5" ${screenSize === "1.5" ? "selected" : ""}>1.5x</option>
                  <option value="2" ${screenSize === "2" ? "selected" : ""}>2x</option>
                  <option value="3" ${screenSize === "3" ? "selected" : ""}>3x</option>
                  <option value="fit" ${screenSize === "fit" ? "selected" : ""}>Fit</option>
                </select>`
              : ""
          }
          ${
            entries.length > 1
              ? `<select id="entry">${entries
                  .map(
                    (entry, index) =>
                      `<option value="${index}" ${index === currentIndex ? "selected" : ""}>${this._escape(
                        entry.title,
                      )}</option>`,
                  )
                  .join("")}</select>`
              : ""
          }
        </div>
        ${
          !selected
            ? `<div class="message">Configure a NanoKVM Pro Desk screen agent first.</div>`
            : `<div class="content">
                ${
                  setupRequired
                    ? `<div class="setup-callout">
                        <div>
                          <div class="setup-title">${
                            selected.agent_configured
                              ? "Agent is not reachable"
                              : "Agent setup required"
                          }</div>
                          <div class="setup-text">
                            ${
                              selected.agent_configured
                                ? "Desk token is configured, but Home Assistant cannot reach the agent right now. Check status, reinstall/update, or verify network and port."
                                : "Install or connect the Desk agent to enable the screen and controls. SSH is only used for setup."
                            }
                          </div>
                        </div>
                        <button type="button" data-open-agent class="primary-agent large">
                          ${selected.agent_configured ? "Manage agent" : "Set up agent"}
                        </button>
                      </div>`
                    : ""
                }
                <div class="viewer" id="viewer">
                  <div class="screen-column" id="screen-column">
                    <div id="status" class="screen-badge">${
                      agentReachable ? "agent reachable" : "agent not reachable"
                    }</div>
                    <div class="screen" id="screen">
                      <img id="screen-image" alt="NanoKVM Pro Desk screen">
                      <div class="screen-status" id="screen-status">Loading screen...</div>
                    </div>
                  </div>
                  <div class="controls" aria-label="Desk controls">
                    <button type="button" data-action="left" title="Rotate left">↺</button>
                    <button type="button" data-action="click" title="Click">⏎</button>
                    <button type="button" data-action="long-click" title="Long press">Long press</button>
                    <button type="button" data-action="right" title="Rotate right">↻</button>
                  </div>
                </div>
              </div>
              ${this._agentDialogTemplate(selected)}`
        }
      </div>
    `;

    const select = this.shadowRoot.getElementById("entry");
    if (select) {
      select.addEventListener("change", (event) => {
        this._selectedIndex = event.target.value;
        this._render();
      });
    }

    this._selected = selected;
    this._applyScreenSize(screenSize);
    this._wireControls();
    this._wireAgentDialog(selected);
    this._startRefresh();
  }

  _agentDialogTemplate(selected) {
    if (!this._agentDialogOpen) {
      return "";
    }

    const host = this._escape(selected.host || "");
    const port = this._escape(selected.port || "8765");
    const message = this._escape(this._agentMessage || "");
    return `
      <div class="modal-backdrop" id="agent-modal">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="agent-title">
          <h2 id="agent-title">Desk agent</h2>
          <div class="security-note">
            This installs or removes a root service under
            <code>/userapp/nanokvm-desk-agent</code>. SSH is used only for this
            action, the SSH password is not stored, and normal runtime uses the
            token-protected HTTP agent. The Desk token is saved server-side and
            is not displayed here. Keep it on a trusted LAN or VPN.
            <a href="${SECURITY_URL}" target="_blank" rel="noreferrer">Security notes</a>
          </div>
          <form id="agent-form" class="agent-form">
            <div class="field">
              <label for="agent-ssh-host">SSH host</label>
              <input id="agent-ssh-host" autocomplete="off" value="${host}">
            </div>
            <div class="field">
              <label for="agent-ssh-user">SSH user</label>
              <input id="agent-ssh-user" autocomplete="username" value="root">
            </div>
            <div class="field">
              <label for="agent-ssh-password">SSH password</label>
              <input id="agent-ssh-password" type="password" autocomplete="current-password">
            </div>
            <div class="field">
              <label for="agent-ssh-port">SSH port</label>
              <input id="agent-ssh-port" type="number" min="1" max="65535" value="22">
            </div>
            <div class="field">
              <label for="agent-port">Agent HTTP port</label>
              <input id="agent-port" type="number" min="1" max="65535" value="${port}">
            </div>
          </form>
          <div class="agent-actions">
            <button type="button" data-agent-action="install">Install / update</button>
            <button type="button" data-agent-action="reset-token">Reset token</button>
            <button type="button" data-agent-action="status">Check status</button>
            <button type="button" data-agent-action="uninstall">Uninstall</button>
            <button type="button" id="agent-close">Close</button>
          </div>
          <div id="agent-message" class="agent-message">${message}</div>
        </div>
      </div>
    `;
  }

  _applyScreenSize(size) {
    const viewer = this.shadowRoot?.getElementById("viewer");
    const screenColumn = this.shadowRoot?.getElementById("screen-column");
    if (!viewer || !screenColumn) {
      return;
    }

    this._screenSize = size;
    localStorage.setItem("nanokvmDeskScreenSize", size);
    viewer.dataset.screenSize = size;
    if (size === "fit") {
      screenColumn.style.removeProperty("--screen-width");
      return;
    }
    screenColumn.style.setProperty("--screen-width", `${Math.round(320 * Number(size))}px`);
  }

  _wireControls() {
    if (!this._selected || !this.shadowRoot) {
      return;
    }

    this.shadowRoot.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", () => this._handleButton(button.dataset.action));
    });

    const sizeSelect = this.shadowRoot.getElementById("screen-size");
    if (sizeSelect) {
      sizeSelect.addEventListener("change", (event) => {
        this._applyScreenSize(event.target.value);
      });
    }

    const screen = this.shadowRoot.getElementById("screen");
    if (!screen) {
      return;
    }

    screen.addEventListener("pointerdown", (event) => {
      screen.setPointerCapture(event.pointerId);
      this._pointerStart = {
        id: event.pointerId,
        point: this._eventPoint(event),
        time: Date.now(),
      };
    });

    screen.addEventListener("pointerup", (event) => {
      if (!this._pointerStart || this._pointerStart.id !== event.pointerId) {
        return;
      }
      const start = this._pointerStart.point;
      const end = this._eventPoint(event);
      this._pointerStart = null;
      const distance = Math.hypot(end.x - start.x, end.y - start.y);
      if (distance < 8) {
        this._postInput("tap", { x: end.x, y: end.y });
        return;
      }
      this._postInput("swipe", {
        start_x: start.x,
        start_y: start.y,
        end_x: end.x,
        end_y: end.y,
      });
    });
  }

  _wireAgentDialog(selected) {
    this.shadowRoot?.querySelectorAll("button[data-open-agent]").forEach((button) => {
      button.addEventListener("click", () => {
        this._agentDialogOpen = true;
        this._agentMessage = "";
        this._render();
      });
    });

    if (!selected || !this._agentDialogOpen) {
      return;
    }

    const close = this.shadowRoot.getElementById("agent-close");
    if (close) {
      close.addEventListener("click", () => {
        this._agentDialogOpen = false;
        this._agentMessage = "";
        this._render();
      });
    }

    this.shadowRoot.querySelectorAll("button[data-agent-action]").forEach((button) => {
      button.addEventListener("click", () => this._handleAgentAction(button.dataset.agentAction));
    });
  }

  async _handleAgentAction(action) {
    if (action === "uninstall") {
      const confirmed = window.confirm(
        "Uninstall the on-device Desk agent from this NanoKVM Pro Desk?",
      );
      if (!confirmed) {
        return;
      }
    }

    if (action === "reset-token") {
      await this._postAgent("install", { reset_token: true });
      return;
    }

    await this._postAgent(action);
  }

  _readAgentForm() {
    return {
      ssh_host: this.shadowRoot.getElementById("agent-ssh-host").value.trim(),
      ssh_user: this.shadowRoot.getElementById("agent-ssh-user").value.trim(),
      ssh_password: this.shadowRoot.getElementById("agent-ssh-password").value,
      ssh_port: Number(this.shadowRoot.getElementById("agent-ssh-port").value || 22),
      agent_port: Number(this.shadowRoot.getElementById("agent-port").value || 8765),
      bind: "0.0.0.0",
      fps: 12,
    };
  }

  async _postAgent(action, extra = {}) {
    if (!this._selected) {
      return;
    }
    this._setAgentBusy(true);
    this._setAgentMessage("running...");

    try {
      const response = await this._hass.fetchWithAuth(`${this._selected.agent_url}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...this._readAgentForm(), ...extra }),
      });
      const data = await this._responseJson(response);
      if (!response.ok) {
        throw new Error(data.message || `${response.status} ${response.statusText}`);
      }

      this._applyAgentResult(action, data);
      this._setAgentMessage(this._agentResultMessage(action, data));
    } catch (err) {
      this._setAgentMessage(`failed: ${err.message}`);
    } finally {
      this._setAgentBusy(false);
    }
  }

  async _responseJson(response) {
    try {
      const data = await response.json();
      return data && typeof data === "object" ? data : {};
    } catch (_err) {
      return {};
    }
  }

  _applyAgentResult(action, data) {
    if (action === "install") {
      this._selected.host = data.host || this._selected.host;
      this._selected.port = data.port || this._selected.port;
      this._selected.agent_configured = true;
      this._selected.agent_installed = true;
      this._setStatus("agent updated");
      return;
    }
    if (action === "uninstall") {
      if (data.ok) {
        this._selected.agent_configured = false;
        this._selected.agent_installed = false;
      }
      this._setStatus(data.ok ? "agent uninstalled" : "uninstall failed");
    }
  }

  _agentResultMessage(action, data) {
    if (action === "status") {
      if (!data.installed) {
        return "agent is not installed";
      }
      const manager = data.service_manager || "unknown service manager";
      return data.active
        ? `agent installed and active via ${manager}`
        : `agent installed but not active via ${manager}`;
    }
    if (action === "install") {
      return `agent installed via ${data.service_manager}; Desk token updated in Home Assistant`;
    }
    if (action === "uninstall") {
      return data.ok ? "agent uninstalled" : "uninstall command failed";
    }
    return "done";
  }

  _setAgentBusy(busy) {
    this.shadowRoot?.querySelectorAll("button[data-agent-action]").forEach((button) => {
      button.disabled = busy;
    });
  }

  _setAgentMessage(message) {
    this._agentMessage = message;
    const element = this.shadowRoot?.getElementById("agent-message");
    if (element) {
      element.textContent = message;
    }
  }

  _startRefresh() {
    this._stopRefresh();
    if (!this._selected || !this.shadowRoot) {
      return;
    }

    const image = this.shadowRoot.getElementById("screen-image");
    if (!image) {
      return;
    }

    let stopped = false;
    const refresh = async () => {
      if (stopped || !this.isConnected || !this._selected || !this._hass) {
        return;
      }
      let ok = false;
      try {
        const response = await this._hass.fetchWithAuth(this._selected.snapshot_url);
        if (response.ok) {
          const url = URL.createObjectURL(await response.blob());
          URL.revokeObjectURL(image.src);
          image.src = url;
          ok = true;
        }
      } catch (_err) {
        // fall through to the unavailable state
      }
      if (stopped) {
        return;
      }
      this._setAgentReachable(ok);
      this._setStatus(ok ? "live" : "screen unavailable");
      this._setScreenMessage(ok ? "" : "Screen snapshot unavailable");
      // _setAgentReachable may have re-rendered and started a new loop.
      if (!stopped) {
        this._refreshTimer = window.setTimeout(refresh, ok ? 350 : 1500);
      }
    };

    this._stopRefresh = () => {
      stopped = true;
      URL.revokeObjectURL(image.src);
      if (this._refreshTimer) {
        window.clearTimeout(this._refreshTimer);
        this._refreshTimer = undefined;
      }
    };

    this._setStatus("loading");
    this._setScreenMessage("Loading screen...");
    refresh();
  }

  _stopRefresh() {}

  _handleButton(action) {
    if (action === "left" || action === "right") {
      this._postInput("knob_rotate", {
        direction: action,
        notches: 1,
        steps_per_notch: 2,
      });
    } else if (action === "click") {
      this._postInput("knob_click", { press_seconds: 0.05 });
    } else if (action === "long-click") {
      this._postInput("knob_click", { press_seconds: 1.0 });
    }
  }

  async _postInput(action, payload) {
    if (!this._selected) {
      return;
    }
    this._setStatus("sending");
    try {
      const response = await this._hass.fetchWithAuth(`${this._selected.input_url}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      this._setStatus("live");
    } catch (err) {
      this._setStatus(`input failed: ${err.message}`);
    }
  }

  _eventPoint(event) {
    const image = this.shadowRoot.getElementById("screen-image");
    const rect = image.getBoundingClientRect();
    const width = image.naturalWidth || 320;
    const height = image.naturalHeight || 172;
    return {
      x: Math.max(0, Math.min(width - 1, ((event.clientX - rect.left) * width) / rect.width)),
      y: Math.max(0, Math.min(height - 1, ((event.clientY - rect.top) * height) / rect.height)),
    };
  }

  _setStatus(message) {
    const status = this.shadowRoot?.getElementById("status");
    if (status) {
      status.textContent = message;
    }
  }

  _setScreenMessage(message) {
    const status = this.shadowRoot?.getElementById("screen-status");
    if (!status) {
      return;
    }
    status.textContent = message;
    status.hidden = !message;
  }

  _escape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  _setAgentReachable(reachable) {
    if (!this._selected || this._selected.agent_installed === reachable) {
      return;
    }
    this._selected.agent_installed = reachable;
    this._render();
  }
}

customElements.define("nanokvm-pro-desk-screen-panel", NanoKVMProDeskScreenPanel);
