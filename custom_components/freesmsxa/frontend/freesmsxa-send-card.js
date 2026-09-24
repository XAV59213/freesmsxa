const CARD_TAG = "freesmsxa-send-card";
const EDITOR_TAG = "freesmsxa-send-card-editor";

class FreeSMSXASendCard extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._dest = "__all__";
    this._message = "";
    this._status = "";
    this._sending = false;
    this._built = false;
    this.attachShadow({ mode: "open" });
  }

  static getStubConfig() {
    return {};
  }

  static getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  setConfig(config) {
    this._config = config || {};
    if (this._built) this._applyLabels();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._build();
      this._built = true;
    }
    this._syncDestinations();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { rows: 6, columns: 12, min_rows: 5, min_columns: 6, max_rows: 8 };
  }

  _isFr() {
    const lang = (this._hass && this._hass.language) || "fr";
    return String(lang).toLowerCase().startsWith("fr");
  }

  _labels() {
    if (this._isFr()) {
      return {
        title: this._config.title || "Envoyer un SMS",
        dest: "Destinataire",
        message: "Message",
        placeholder: "Saisis ton message…",
        send: "Envoyer",
        all: "TOUS LE MONDE !",
        empty: "Saisis un message avant d’envoyer.",
        none: "Aucune ligne Free Mobile SMS XA trouvée.",
        ok: "SMS envoyé.",
        error: "Échec de l’envoi.",
      };
    }
    return {
      title: this._config.title || "Send SMS",
      dest: "Recipient",
      message: "Message",
      placeholder: "Type your message…",
      send: "Send",
      all: "EVERYONE",
      empty: "Enter a message before sending.",
      none: "No Free Mobile SMS XA notify entity found.",
      ok: "SMS sent.",
      error: "Send failed.",
    };
  }

  _notifyEntities() {
    if (!this._hass) return [];
    const states = this._hass.states || {};
    const entities = this._hass.entities || {};
    const found = [];
    for (const entityId of Object.keys(states)) {
      if (!entityId.startsWith("notify.")) continue;
      const meta = entities[entityId] || {};
      const platform = meta.platform || "";
      if (platform === "freesmsxa" || String(entityId).includes("freesms")) {
        found.push(entityId);
      }
    }
    if (found.length) return found.sort();
    return Object.keys(states).filter((id) => id.startsWith("notify.")).sort();
  }

  _nameOf(entityId) {
    const state = this._hass.states[entityId];
    return (state && (state.attributes.friendly_name || state.attributes.name)) || entityId.replace("notify.", "");
  }

  _build() {
    const labels = this._labels();
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; height: 100%; }
        ha-card { height: 100%; display: flex; flex-direction: column; overflow: hidden; box-sizing: border-box; }
        .wrap { flex: 1; min-height: 0; padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 8px; box-sizing: border-box; }
        h2 { margin: 0; font-size: 16px; font-weight: 500; }
        label { font-size: 12px; opacity: 0.75; display: block; margin-bottom: 4px; }
        .row-label { display: flex; justify-content: space-between; align-items: baseline; }
        .count { font-size: 11px; opacity: 0.7; }
        select, textarea {
          width: 100%; box-sizing: border-box; border-radius: 10px;
          border: 1px solid var(--divider-color);
          background: var(--input-fill-color, var(--secondary-background-color));
          color: var(--primary-text-color); padding: 8px 10px; font: inherit;
        }
        textarea { min-height: 44px; max-height: 72px; resize: none; flex: 1; }
        .actions { display: flex; justify-content: center; padding-top: 2px; flex-shrink: 0; }
        button {
          display: inline-flex; align-items: center; justify-content: center; border: none;
          border-radius: 12px; padding: 10px 20px; font: inherit; font-weight: 600; cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, #fff);
        }
        button:disabled { opacity: 0.6; cursor: default; }
        .status { text-align: center; font-size: 12px; min-height: 1em; opacity: 0.85; flex-shrink: 0; }
      </style>
      <ha-card>
        <div class="wrap">
          <h2 id="title">${labels.title}</h2>
          <div>
            <label id="dest-label">${labels.dest}</label>
            <select id="dest"></select>
          </div>
          <div style="display:flex;flex-direction:column;flex:1;min-height:0;">
            <div class="row-label">
              <label id="msg-label">${labels.message}</label>
              <span class="count" id="count">0 / 160</span>
            </div>
            <textarea id="msg" maxlength="160" placeholder="${labels.placeholder}"></textarea>
          </div>
          <div class="actions"><button id="send">${labels.send}</button></div>
          <div class="status" id="status"></div>
        </div>
      </ha-card>
    `;
    this._els = {
      title: this.shadowRoot.getElementById("title"),
      destLabel: this.shadowRoot.getElementById("dest-label"),
      dest: this.shadowRoot.getElementById("dest"),
      msgLabel: this.shadowRoot.getElementById("msg-label"),
      msg: this.shadowRoot.getElementById("msg"),
      count: this.shadowRoot.getElementById("count"),
      send: this.shadowRoot.getElementById("send"),
      status: this.shadowRoot.getElementById("status"),
    };
    this._els.dest.addEventListener("change", (ev) => { this._dest = ev.target.value; });
    this._els.msg.addEventListener("input", (ev) => {
      this._message = ev.target.value;
      this._els.count.textContent = `${this._message.length} / 160`;
    });
    this._els.send.addEventListener("click", () => this._send());
  }

  _applyLabels() {
    if (!this._els) return;
    const labels = this._labels();
    this._els.title.textContent = labels.title;
    this._els.destLabel.textContent = labels.dest;
    this._els.msgLabel.textContent = labels.message;
    this._els.msg.placeholder = labels.placeholder;
    this._els.send.textContent = labels.send;
  }

  _syncDestinations() {
    if (!this._els) return;
    const labels = this._labels();
    const targets = this._notifyEntities();
    const current = this._els.dest.value || this._dest;
    const html = [`<option value="__all__">${labels.all}</option>`]
      .concat(targets.map((id) => `<option value="${id}">${this._nameOf(id)}</option>`))
      .join("");
    if (this._els.dest.innerHTML !== html) this._els.dest.innerHTML = html;
    this._dest = targets.includes(current) || current === "__all__" ? current : "__all__";
    this._els.dest.value = this._dest;
  }

  async _send() {
    const labels = this._labels();
    const message = (this._message || "").trim();
    if (!message) { this._els.status.textContent = labels.empty; return; }
    const targets = this._notifyEntities();
    if (!targets.length) { this._els.status.textContent = labels.none; return; }
    const selected = this._dest === "__all__" ? targets : [this._dest];
    this._els.send.disabled = true;
    this._els.status.textContent = "";
    try {
      await this._hass.callService("notify", "send_message", { entity_id: selected, message });
      this._message = "";
      this._els.msg.value = "";
      this._els.count.textContent = "0 / 160";
      this._els.status.textContent = labels.ok;
    } catch (err) {
      this._els.status.textContent = `${labels.error} ${err?.message || err}`;
    } finally {
      this._els.send.disabled = false;
    }
  }
}

class FreeSMSXASendCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this.attachShadow({ mode: "open" });
  }
  setConfig(config) {
    this._config = { ...(config || {}) };
    this._render();
  }
  set hass(_hass) {}
  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        .box { padding: 8px 0; display: flex; flex-direction: column; gap: 6px; }
        label { font-size: 13px; }
        input {
          padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color);
          background: var(--card-background-color); color: var(--primary-text-color); font: inherit;
        }
      </style>
      <div class="box">
        <label>Titre</label>
        <input id="title" type="text" value="${this._config.title || ""}" placeholder="Envoyer un SMS" />
      </div>
    `;
    this.shadowRoot.getElementById("title").addEventListener("change", (ev) => {
      this._config = { ...this._config, title: ev.target.value };
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config } }));
    });
  }
}

if (!customElements.get(CARD_TAG)) customElements.define(CARD_TAG, FreeSMSXASendCard);
if (!customElements.get(EDITOR_TAG)) customElements.define(EDITOR_TAG, FreeSMSXASendCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TAG)) {
  window.customCards.push({
    type: CARD_TAG,
    name: "Envoyer un SMS",
    description: "Envoie un SMS via Free Mobile SMS XA",
    preview: true,
    documentationURL: "https://github.com/XAV59213/freesmsxa",
  });
}
