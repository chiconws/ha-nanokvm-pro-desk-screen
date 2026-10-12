const REPO_URL = "https://github.com/chiconws/ha-nanokvm-pro-desk-screen";
const SECURITY_URL = `${REPO_URL}/blob/main/SECURITY.md`;
const AGENT_SOURCE_PATH = "custom_components/nanokvm_pro_desk_screen/agent/runtime.py";
const HOST_KEY_COMMAND = "for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf $f; done";

const STRINGS = {
  en: {
    title: "NanoKVM Pro Desk Screen",
    manage_agent: "Manage agent",
    setup_agent: "Set up agent",
    update_agent: "Update agent",
    screen_size: "Screen size",
    fit: "Fit",
    no_entries: "Add a NanoKVM Pro Desk Screen entry first.",
    callout_setup_title: "Agent setup required",
    callout_setup_text:
      "Install the Desk agent to enable the screen and controls. SSH is only used for setup.",
    callout_unreachable_title: "Agent is not reachable",
    callout_unreachable_text:
      "A token is configured, but Home Assistant cannot reach the agent right now. Reinstall or update it, or check the network and port.",
    callout_outdated_title: "Agent update available",
    callout_outdated_text:
      "The agent on the Desk is older than this integration. Update it to get the latest fixes.",
    badge_reachable: "agent reachable",
    badge_unreachable: "agent not reachable",
    screen_alt: "NanoKVM Pro Desk screen",
    loading: "loading",
    loading_screen: "Loading screen...",
    live: "live",
    sending: "sending",
    screen_unavailable: "screen unavailable",
    snapshot_unavailable: "Screen snapshot unavailable",
    input_failed: "input failed: {error}",
    controls: "Desk controls",
    rotate_left: "Rotate left",
    click: "Click",
    long_press: "Long press",
    rotate_right: "Rotate right",
    dialog_title: "Desk agent",
    close: "Close",
    sec_root:
      "Installs a service that runs as <b>root</b> on the Desk, in <code>/userapp/nanokvm-desk-agent</code>.",
    sec_code: "View the exact code that will be installed",
    sec_code_github: "this version on GitHub",
    sec_code_failed: "Could not load the agent code.",
    sec_api: "Its API only exposes the front screen and touch and knob input.",
    sec_http:
      "It listens on port {port} over <b>unencrypted HTTP</b>, protected by a token. Anyone who captures the token on the network gets the same access: keep the Desk on a trusted LAN or VPN.",
    sec_secrets:
      "The SSH password is used only for this action and is not saved. The token stays in Home Assistant and is not shown here.",
    sec_link: "Security notes",
    status_checking: "Checking the agent...",
    status_error: "Could not check the agent.",
    status_not_installed: "Not installed: Home Assistant has no token for this Desk.",
    status_unreachable: "A token is configured, but the agent does not answer on {host}:{port}.",
    status_outdated: "Running, but older than this integration. Install / update to refresh it.",
    status_ok: "Running and up to date.",
    ssh_password: "SSH password",
    advanced: "Advanced",
    ssh_host: "SSH host",
    ssh_user: "SSH user",
    ssh_port: "SSH port",
    agent_port: "Agent HTTP port",
    install: "Install / update",
    reset_token: "Reset token",
    uninstall: "Uninstall",
    running: "Running...",
    failed: "Failed: {error}",
    done_install: "Agent installed via {manager}. Token saved in Home Assistant.",
    done_uninstall: "Agent uninstalled.",
    uninstall_failed: "Uninstall left files on the Desk: {error}",
    confirm_uninstall_title: "Uninstall the agent?",
    confirm_uninstall_text:
      "This stops the service and removes it from the Desk. The screen and controls stop working until you install it again.",
    hostkey_new_title: "Confirm the Desk's SSH host key",
    hostkey_new_text:
      "This is the first SSH connection from Home Assistant to {host}. The password has not been sent yet.",
    hostkey_changed_title: "The SSH host key has changed",
    hostkey_changed_text:
      "{host} presents a different key from the one you trusted before. Unless you reinstalled the Desk, do not continue. The password has not been sent.",
    hostkey_compare: "Compare it with the output of this command on the Desk:",
    trust_key: "Trust this key",
    cancel: "Cancel",
    hostkey_rejected: "SSH host key not trusted",
  },
  "pt-BR": {
    manage_agent: "Gerenciar agente",
    setup_agent: "Configurar agente",
    update_agent: "Atualizar agente",
    screen_size: "Tamanho da tela",
    fit: "Ajustar",
    no_entries: "Adicione primeiro uma entrada do NanoKVM Pro Desk Screen.",
    callout_setup_title: "É preciso instalar o agente",
    callout_setup_text:
      "Instale o agente no Desk para habilitar a tela e os controles. O SSH só é usado na instalação.",
    callout_unreachable_title: "O agente não responde",
    callout_unreachable_text:
      "Há um token configurado, mas o Home Assistant não consegue falar com o agente agora. Reinstale ou atualize, ou verifique a rede e a porta.",
    callout_outdated_title: "Atualização do agente disponível",
    callout_outdated_text:
      "O agente no Desk é mais antigo que esta integração. Atualize para receber as correções mais recentes.",
    badge_reachable: "agente acessível",
    badge_unreachable: "agente inacessível",
    screen_alt: "Tela do NanoKVM Pro Desk",
    loading: "carregando",
    loading_screen: "Carregando a tela...",
    live: "ao vivo",
    sending: "enviando",
    screen_unavailable: "tela indisponível",
    snapshot_unavailable: "Captura da tela indisponível",
    input_failed: "falha no comando: {error}",
    controls: "Controles do Desk",
    rotate_left: "Girar para a esquerda",
    click: "Clique",
    long_press: "Clique longo",
    rotate_right: "Girar para a direita",
    dialog_title: "Agente do Desk",
    close: "Fechar",
    sec_root:
      "Instala um serviço que roda como <b>root</b> no Desk, em <code>/userapp/nanokvm-desk-agent</code>.",
    sec_code: "Ver o código exato que será instalado",
    sec_code_github: "esta versão no GitHub",
    sec_code_failed: "Não foi possível carregar o código do agente.",
    sec_api: "A API dele só expõe a tela frontal e o envio de toque e knob.",
    sec_http:
      "Ele escuta na porta {port} em <b>HTTP sem criptografia</b>, protegido por um token. Quem capturar o token na rede ganha o mesmo acesso: mantenha o Desk em uma LAN confiável ou VPN.",
    sec_secrets:
      "A senha SSH é usada só nesta ação e não é salva. O token fica no Home Assistant e não aparece aqui.",
    sec_link: "Notas de segurança",
    status_checking: "Verificando o agente...",
    status_error: "Não foi possível verificar o agente.",
    status_not_installed: "Não instalado: o Home Assistant não tem token para este Desk.",
    status_unreachable: "Há um token configurado, mas o agente não responde em {host}:{port}.",
    status_outdated:
      "Rodando, mas mais antigo que esta integração. Use Instalar / atualizar para renová-lo.",
    status_ok: "Rodando e atualizado.",
    ssh_password: "Senha SSH",
    advanced: "Avançado",
    ssh_host: "Host SSH",
    ssh_user: "Usuário SSH",
    ssh_port: "Porta SSH",
    agent_port: "Porta HTTP do agente",
    install: "Instalar / atualizar",
    reset_token: "Redefinir token",
    uninstall: "Desinstalar",
    running: "Executando...",
    failed: "Falhou: {error}",
    done_install: "Agente instalado via {manager}. Token salvo no Home Assistant.",
    done_uninstall: "Agente desinstalado.",
    uninstall_failed: "A desinstalação deixou arquivos no Desk: {error}",
    confirm_uninstall_title: "Desinstalar o agente?",
    confirm_uninstall_text:
      "Isto para o serviço e o remove do Desk. A tela e os controles deixam de funcionar até você instalar de novo.",
    hostkey_new_title: "Confirme a chave SSH do Desk",
    hostkey_new_text:
      "Esta é a primeira conexão SSH do Home Assistant com {host}. A senha ainda não foi enviada.",
    hostkey_changed_title: "A chave SSH do host mudou",
    hostkey_changed_text:
      "{host} apresenta uma chave diferente da que você confiou antes. A menos que você tenha reinstalado o Desk, não continue. A senha não foi enviada.",
    hostkey_compare: "Compare com a saída deste comando no Desk:",
    trust_key: "Confiar nesta chave",
    cancel: "Cancelar",
    hostkey_rejected: "Chave SSH do host não confiada",
  },
};

class NanoKVMProDeskScreenPanel extends HTMLElement {
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      // Language and authenticated fetches are only available from here on.
      this._render();
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

  _t(key, vars = {}) {
    const language = this._hass?.language || "en";
    const table = language.startsWith("pt") ? STRINGS["pt-BR"] : STRINGS.en;
    const text = table[key] ?? STRINGS.en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_match, name) => vars[name] ?? "");
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
    if (selected !== this._selected) {
      this._agentStatus = undefined;
    }
    const callout = this._callout();
    const agentButton = this._t(
      { setup: "setup_agent", outdated: "update_agent" }[callout] || "manage_agent",
    );

    // Re-rendering replaces the whole DOM; carry what the user typed across it.
    const kept = {};
    this.shadowRoot.querySelectorAll("#agent-form input").forEach((input) => {
      kept[input.id] = input.value;
    });
    const advancedOpen = this.shadowRoot.getElementById("agent-advanced")?.open;
    const focusedId = this.shadowRoot.activeElement?.id;

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
        [hidden] {
          display: none !important;
        }
        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .modal-header h2 {
          margin: 0;
        }
        .icon-button {
          min-height: 32px;
          width: 32px;
          padding: 0;
          border: none;
          background: none;
          font-size: 18px;
        }
        .agent-status {
          display: flex;
          gap: 8px;
          align-items: baseline;
          margin-bottom: 12px;
          padding: 8px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          line-height: 1.4;
        }
        .agent-status::before {
          content: "\\25CF";
          color: var(--secondary-text-color);
        }
        .agent-status.ok::before {
          color: var(--success-color, #43a047);
        }
        .agent-status.warn::before {
          color: var(--warning-color, #ffa600);
        }
        .agent-status.bad::before {
          color: var(--error-color, #db4437);
        }
        ul.security-note {
          margin-top: 0;
          padding-left: 28px;
        }
        ul.security-note li + li {
          margin-top: 4px;
        }
        details {
          margin: 12px 0;
        }
        summary {
          margin-bottom: 8px;
          color: var(--secondary-text-color);
          cursor: pointer;
        }
        .agent-actions .spacer {
          flex: 1;
        }
        button.danger {
          color: var(--error-color, #db4437);
          border-color: var(--error-color, #db4437);
        }
        button.danger:hover {
          background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent);
        }
        .confirm {
          margin-bottom: 12px;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
        }
        .confirm.danger {
          border-color: var(--error-color, #db4437);
        }
        .confirm-title {
          margin-bottom: 8px;
          font-weight: 600;
        }
        .confirm p {
          margin: 8px 0;
          line-height: 1.4;
        }
        pre {
          margin: 8px 0;
          padding: 8px;
          overflow: auto;
          background: var(--secondary-background-color);
          border-radius: 4px;
          white-space: pre-wrap;
          word-break: break-all;
          user-select: all;
        }
        .agent-message.busy::before {
          content: "";
          display: inline-block;
          width: 12px;
          height: 12px;
          margin-right: 8px;
          border: 2px solid var(--divider-color);
          border-top-color: var(--primary-color);
          border-radius: 50%;
          vertical-align: -2px;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
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
                  class="${callout ? "primary-agent" : ""}"
                >${agentButton}</button>
                <select id="screen-size" title="${this._t("screen_size")}" aria-label="${this._t("screen_size")}">
                  ${["1", "1.5", "2", "3"]
                    .map(
                      (size) =>
                        `<option value="${size}" ${screenSize === size ? "selected" : ""}>${size}x</option>`,
                    )
                    .join("")}
                  <option value="fit" ${screenSize === "fit" ? "selected" : ""}>${this._t("fit")}</option>
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
            ? `<div class="message">${this._t("no_entries")}</div>`
            : `<div class="content">
                ${
                  callout
                    ? `<div class="setup-callout">
                        <div>
                          <div class="setup-title">${this._t(`callout_${callout}_title`)}</div>
                          <div class="setup-text">${this._t(`callout_${callout}_text`)}</div>
                        </div>
                        <button type="button" data-open-agent class="primary-agent large">
                          ${agentButton}
                        </button>
                      </div>`
                    : ""
                }
                <div class="viewer" id="viewer">
                  <div class="screen-column" id="screen-column">
                    <div id="status" class="screen-badge">${this._t("loading")}</div>
                    <div class="screen" id="screen">
                      <img id="screen-image" alt="${this._t("screen_alt")}">
                      <div class="screen-status" id="screen-status">${this._t("loading_screen")}</div>
                    </div>
                  </div>
                  <div class="controls" aria-label="${this._t("controls")}">
                    <button type="button" data-action="left" title="${this._t("rotate_left")}">↺</button>
                    <button type="button" data-action="click" title="${this._t("click")}">⏎</button>
                    <button type="button" data-action="long-click" title="${this._t("long_press")}">${this._t("long_press")}</button>
                    <button type="button" data-action="right" title="${this._t("rotate_right")}">↻</button>
                  </div>
                </div>
              </div>
              ${this._agentDialogTemplate(selected)}`
        }
      </div>
    `;

    for (const [id, value] of Object.entries(kept)) {
      const input = this.shadowRoot.getElementById(id);
      if (input) {
        input.value = value;
      }
    }
    const advanced = this.shadowRoot.getElementById("agent-advanced");
    if (advanced && advancedOpen) {
      advanced.open = true;
    }
    if (focusedId) {
      this.shadowRoot.getElementById(focusedId)?.focus();
    }

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
    if (selected && this._agentStatus === undefined) {
      this._loadAgentStatus();
    }
  }

  // Which notice the page shows, from the last agent state read from the server.
  _callout() {
    const status = this._agentStatus;
    if (!status) {
      return "";
    }
    if (!status.configured) {
      return "setup";
    }
    if (!status.reachable) {
      return "unreachable";
    }
    return status.outdated ? "outdated" : "";
  }

  _agentDialogTemplate(selected) {
    if (!this._agentDialogOpen) {
      return "";
    }

    const host = this._escape(this._agentStatus?.host || "");
    const port = this._escape(this._agentStatus?.port || "8765");
    const confirm = this._agentConfirm;
    const status = this._agentStatusView();
    const disabled = this._agentBusy ? "disabled" : "";
    return `
      <div class="modal-backdrop" id="agent-modal">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="agent-title">
          <div class="modal-header">
            <h2 id="agent-title">${this._t("dialog_title")}</h2>
            <button type="button" id="agent-close" class="icon-button" aria-label="${this._t("close")}" title="${this._t("close")}">✕</button>
          </div>
          <div id="agent-status" class="agent-status ${status.level}">${this._escape(status.text)}</div>
          ${
            confirm
              ? `<div class="confirm ${confirm.danger ? "danger" : ""}">
                  <div class="confirm-title">${this._escape(confirm.title)}</div>
                  <p>${this._escape(confirm.text)}</p>
                  ${(confirm.blocks || [])
                    .map(
                      (block) =>
                        `${block.label ? `<p>${this._escape(block.label)}</p>` : ""}<pre>${this._escape(block.code)}</pre>`,
                    )
                    .join("")}
                  <div class="agent-actions">
                    <button type="button" data-confirm="yes" class="${confirm.danger ? "danger" : "primary-agent"}">${this._escape(confirm.accept)}</button>
                    <button type="button" data-confirm="no">${this._t("cancel")}</button>
                  </div>
                </div>`
              : ""
          }
          <div ${confirm ? "hidden" : ""}>
            <ul class="security-note">
              <li>${this._t("sec_root")}
                <a href="#" id="agent-source">${this._t("sec_code")}</a>
                (${
                  this._agentStatus?.bundled_hash
                    ? `<code>${this._escape(this._agentStatus.bundled_hash)}</code>, `
                    : ""
                }<a href="${REPO_URL}/blob/v${this._escape(this._panel.config.version)}/${AGENT_SOURCE_PATH}" target="_blank" rel="noreferrer">${this._t("sec_code_github")}</a>)</li>
              <li>${this._t("sec_api")}</li>
              <li>${this._t("sec_http", { port })}</li>
              <li>${this._t("sec_secrets")}
                <a href="${SECURITY_URL}" target="_blank" rel="noreferrer">${this._t("sec_link")}</a></li>
            </ul>
            <form id="agent-form">
              <div class="field">
                <label for="agent-ssh-password">${this._t("ssh_password")}</label>
                <input id="agent-ssh-password" type="password" autocomplete="current-password">
              </div>
              <details id="agent-advanced">
                <summary>${this._t("advanced")}</summary>
                <div class="agent-form">
                  <div class="field">
                    <label for="agent-ssh-host">${this._t("ssh_host")}</label>
                    <input id="agent-ssh-host" autocomplete="off" value="${host}">
                  </div>
                  <div class="field">
                    <label for="agent-ssh-user">${this._t("ssh_user")}</label>
                    <input id="agent-ssh-user" autocomplete="username" value="root">
                  </div>
                  <div class="field">
                    <label for="agent-ssh-port">${this._t("ssh_port")}</label>
                    <input id="agent-ssh-port" type="number" min="1" max="65535" value="22">
                  </div>
                  <div class="field">
                    <label for="agent-port">${this._t("agent_port")}</label>
                    <input id="agent-port" type="number" min="1" max="65535" value="${port}">
                  </div>
                </div>
              </details>
              <div class="agent-actions">
                <button type="submit" class="primary-agent" data-agent-action="install" ${disabled}>${this._t("install")}</button>
                <button type="button" data-agent-action="reset-token" ${disabled}>${this._t("reset_token")}</button>
                <span class="spacer"></span>
                <button type="button" class="danger" data-agent-action="uninstall" ${disabled}>${this._t("uninstall")}</button>
              </div>
            </form>
            <div id="agent-message" class="agent-message ${this._agentBusy ? "busy" : ""}" role="status">${this._escape(
              this._agentMessage || "",
            )}</div>
          </div>
        </div>
      </div>
    `;
  }

  _agentStatusView() {
    const status = this._agentStatus;
    if (this._agentStatusLoading || status === undefined) {
      return { level: "", text: this._t("status_checking") };
    }
    if (status === null) {
      return { level: "bad", text: this._t("status_error") };
    }
    if (!status.configured) {
      return { level: "bad", text: this._t("status_not_installed") };
    }
    if (!status.reachable) {
      return { level: "bad", text: this._t("status_unreachable", status) };
    }
    return status.outdated
      ? { level: "warn", text: this._t("status_outdated") }
      : { level: "ok", text: this._t("status_ok") };
  }

  async _loadAgentStatus() {
    const selected = this._selected;
    if (!selected || !this._hass || this._agentStatusLoading) {
      return;
    }
    this._agentStatusLoading = true;
    this._showAgentStatus();
    let status = null;
    try {
      const response = await this._hass.fetchWithAuth(selected.agent_url);
      if (response.ok) {
        status = await response.json();
      }
    } catch (_err) {
      // shown as "could not check"
    }
    this._agentStatusLoading = false;
    if (selected !== this._selected) {
      // The entry changed while this was in flight: read the current one.
      this._loadAgentStatus();
      return;
    }
    const before = this._callout();
    this._agentStatus = status;
    if (before !== this._callout()) {
      // The notice and the toolbar button behind the dialog depend on it.
      this._render();
    } else {
      this._showAgentStatus();
    }
  }

  _showAgentStatus() {
    const element = this.shadowRoot?.getElementById("agent-status");
    if (element) {
      const status = this._agentStatusView();
      element.className = `agent-status ${status.level}`;
      element.textContent = status.text;
    }
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
        this._loadAgentStatus();
      });
    });

    if (!selected || !this._agentDialogOpen) {
      return;
    }

    this.shadowRoot.getElementById("agent-close")?.addEventListener("click", () => {
      this._agentConfirm?.resolve(false);
      this._agentDialogOpen = false;
      this._agentMessage = "";
      this._render();
    });

    this.shadowRoot.getElementById("agent-source")?.addEventListener("click", (event) => {
      event.preventDefault();
      this._openAgentSource();
    });

    // Enter in any field submits the form, which is the install button.
    this.shadowRoot.getElementById("agent-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      this._handleAgentAction("install");
    });
    this.shadowRoot.querySelectorAll("button[type=button][data-agent-action]").forEach((button) => {
      button.addEventListener("click", () => this._handleAgentAction(button.dataset.agentAction));
    });
    this.shadowRoot.querySelectorAll("button[data-confirm]").forEach((button) => {
      button.addEventListener("click", () =>
        this._agentConfirm?.resolve(button.dataset.confirm === "yes"),
      );
    });
  }

  // Open the file Home Assistant would upload, as served by this installation.
  async _openAgentSource() {
    // Opened before the fetch so the browser ties the new tab to the click.
    const tab = window.open("", "_blank");
    try {
      const response = await this._hass.fetchWithAuth(`${this._selected.agent_url}.py`);
      if (!response.ok) {
        throw new Error(response.statusText);
      }
      const blob = new Blob([await response.text()], { type: "text/plain;charset=utf-8" });
      tab.location.href = URL.createObjectURL(blob);
    } catch (_err) {
      tab?.close();
      this._setAgentMessage(this._t("sec_code_failed"));
    }
  }

  // Show a question inside the dialog; resolves to true when accepted.
  _ask(question) {
    return new Promise((resolve) => {
      this._agentConfirm = {
        ...question,
        resolve: (answer) => {
          this._agentConfirm = null;
          this._render();
          resolve(answer);
        },
      };
      this._render();
    });
  }

  async _handleAgentAction(action) {
    if (this._agentBusy) {
      return;
    }
    if (action === "uninstall") {
      const confirmed = await this._ask({
        title: this._t("confirm_uninstall_title"),
        text: this._t("confirm_uninstall_text"),
        accept: this._t("uninstall"),
        danger: true,
      });
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
    const selected = this._selected;
    if (!selected) {
      return;
    }
    this._setAgentBusy(true);
    this._setAgentMessage(this._t("running"));

    try {
      const body = { ...this._readAgentForm(), ...extra };
      let response;
      let data;
      for (;;) {
        response = await this._hass.fetchWithAuth(`${selected.agent_url}/${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        data = await this._responseJson(response);
        if (response.status !== 409 || !data.host_key) {
          break;
        }
        // The server has not sent the password yet; it wants the host key confirmed.
        const changed = data.reason === "changed";
        const trusted = await this._ask({
          title: this._t(changed ? "hostkey_changed_title" : "hostkey_new_title"),
          text: this._t(changed ? "hostkey_changed_text" : "hostkey_new_text", {
            host: body.ssh_host,
          }),
          blocks: [
            { code: `${data.key_type} ${data.host_key}` },
            { label: this._t("hostkey_compare"), code: HOST_KEY_COMMAND },
          ],
          accept: this._t("trust_key"),
          danger: changed,
        });
        if (!trusted) {
          throw new Error(this._t("hostkey_rejected"));
        }
        body.ssh_host_key = data.host_key;
      }
      if (!response.ok) {
        throw new Error(data.message || `${response.status} ${response.statusText}`);
      }

      if (action === "uninstall" && !data.ok) {
        this._setAgentMessage(this._t("uninstall_failed", { error: data.stderr || data.stdout }));
      } else if (action === "uninstall") {
        this._setAgentMessage(this._t("done_uninstall"));
      } else {
        this._setAgentMessage(this._t("done_install", { manager: data.service_manager }));
      }
    } catch (err) {
      this._setAgentMessage(this._t("failed", { error: err.message }));
    } finally {
      this._setAgentBusy(false);
      this._loadAgentStatus();
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

  _setAgentBusy(busy) {
    this._agentBusy = busy;
    this.shadowRoot?.querySelectorAll("button[data-agent-action]").forEach((button) => {
      button.disabled = busy;
    });
    this.shadowRoot?.getElementById("agent-message")?.classList.toggle("busy", busy);
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
      this._setStatus(this._t(ok ? "live" : "screen_unavailable"));
      this._setScreenMessage(ok ? "" : this._t("snapshot_unavailable"));
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

    this._setStatus(this._t("loading"));
    this._setScreenMessage(this._t("loading_screen"));
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
    this._setStatus(this._t("sending"));
    try {
      const response = await this._hass.fetchWithAuth(`${this._selected.input_url}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      this._setStatus(this._t("live"));
    } catch (err) {
      this._setStatus(this._t("input_failed", { error: err.message }));
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

  // The snapshot loop noticed the agent appear or disappear: read the full state again.
  _setAgentReachable(reachable) {
    if (this._agentStatus && this._agentStatus.reachable !== reachable) {
      this._loadAgentStatus();
    }
  }
}

customElements.define("nanokvm-pro-desk-screen-panel", NanoKVMProDeskScreenPanel);
