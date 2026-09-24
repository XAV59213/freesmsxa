const CARD_TAG = "freesmsxa-send-card";

class FreeSMSXASendCard extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._dest = "__all__";
    this._message = "";
    this._status = "";
    this._sending = false;
    this.attachShadow({ mode: "open" });
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return {
      rows: 6,
      columns: 12,
      min_rows: 5,
      min_columns: 6,
      max_rows: 8,
    };
  }

  _isFr() {
    const lang = (this._hass && this._hass.language) || "fr";
    return String(lang).toLowerCase().startsWith("fr");
  }

  _labels() {
    if (this._isFr()) {
      return {
        title: "Envoyer un SMS",
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
      title: "Send SMS",
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
    return Object.keys(states)
      .filter((id) => id.startsWith("notify."))
      .sort();
  }

  _nameOf(entityId) {
    const state = this._hass.states[entityId];
    return (
      (state && (state.attributes.friendly_name || state.attributes.name)) ||
      entityId.replace("notify.", "")
    );
  }

  async _send() {
    const labels = this._labels();
    const message = (this._message || "").trim();
    if (!message) {
      this._status = labels.empty;
      this._render();
      return;
    }
    const targets = this._notifyEntities();
    if (!targets.length) {
      this._status = labels.none;
      this._render();
      return;
    }
    const selected = this._dest === "__all__" ? targets : [this._dest];
    this._sending = true;
    this._status = "";
    this._render();
    try {
      await this._hass.callService("notify", "send_message", {
        entity_id: selected,
        message,
      });
      this._message = "";
      this._status = labels.ok;
    } catch (err) {
      this._status = `${labels.error} ${err?.message || err}`;
    } finally {
      this._sending = false;
      this._render();
    }
  }

  _render() {
    if (!this.shadowRoot) return;
    const labels = this._labels();
    const targets = this._notifyEntities();
    const options = [`<option value="__all__">${labels.all}</option>`]
      .concat(
        targets.map(
          (id) =>
            `<option value="${id}" ${this._dest === id ? "selected" : ""}>${this._nameOf(id)}</option>`
        )
      )
      .join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
        }
        ha-card {
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          box-sizing: border-box;
        }
        .wrap {
          flex: 1;
          min-height: 0;
          padding: 12px 14px 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          box-sizing: border-box;
        }
        h2 {
          margin: 0;
          font-size: 16px;
          font-weight: 500;
        }
        label {
          font-size: 12px;
          opacity: 0.75;
          display: block;
          margin-bottom: 4px;
        }
        select, textarea {
          width: 100%;
          box-sizing: border-box;
          border-radius: 10px;
          border: 1px solid var(--divider-color);
          background: var(--input-fill-color, var(--secondary-background-color));
          color: var(--primary-text-color);
          padding: 8px 10px;
          font: inherit;
        }
        textarea {
          min-height: 44px;
          max-height: 72px;
          resize: none;
          flex: 1;
        }
        .actions {
          display: flex;
          justify-content: center;
          padding-top: 2px;
          flex-shrink: 0;
        }
        button {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          border: none;
          border-radius: 12px;
          padding: 10px 20px;
          font: inherit;
          font-weight: 600;
          cursor: pointer;
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
        }
        button:disabled { opacity: 0.6; cursor: default; }
        .status {
          text-align: center;
          font-size: 12px;
          min-height: 1em;
          opacity: 0.85;
          flex-shrink: 0;
        }
      </style>
      <ha-card>
        <div class="wrap">
          <h2>${labels.title}</h2>
          <div>
            <label>${labels.dest}</label>
            <select id="dest">${options}</select>
          </div>
          <div style="display:flex;flex-direction:column;flex:1;min-height:0;">
            <label>${labels.message}</label>
            <textarea id="msg" maxlength="160" placeholder="${labels.placeholder}">${this._message.replace(/</g, "&lt;")}</textarea>
          </div>
          <div class="actions">
            <button id="send" ${this._sending ? "disabled" : ""}>${labels.send}</button>
          </div>
          <div class="status">${this._status}</div>
        </div>
      </ha-card>
    `;

    const dest = this.shadowRoot.getElementById("dest");
    const msg = this.shadowRoot.getElementById("msg");
    const send = this.shadowRoot.getElementById("send");
    if (dest) {
      dest.value = targets.includes(this._dest) || this._dest === "__all__" ? this._dest : "__all__";
      dest.addEventListener("change", (ev) => {
        this._dest = ev.target.value;
      });
    }
    if (msg) {
      msg.addEventListener("input", (ev) => {
        this._message = ev.target.value;
      });
    }
    if (send) {
      send.addEventListener("click", () => this._send());
    }
  }
}

if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, FreeSMSXASendCard);
}

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
