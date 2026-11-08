const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const elements=new Map();
class HTMLElement { attachShadow() {this.shadowRoot={innerHTML:"",getElementById(){return {value:"",textContent:"",addEventListener(){}}}};} }
const context={HTMLElement,window:{},customElements:{get:k=>elements.get(k),define:(k,v)=>elements.set(k,v)}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require("node:path").join(__dirname,"../custom_components/freesmsxa/frontend/freesmsxa-send-card.js"),"utf8"), context);
const payload='"><img src=x onerror=alert(1)>&\'';
const Card=elements.get("freesmsxa-send-card"), card=new Card();
card._config={title:payload};card._build();
assert(!card.shadowRoot.innerHTML.includes(payload));assert(card.shadowRoot.innerHTML.includes("&lt;img"));
const Editor=elements.get("freesmsxa-send-card-editor"), editor=new Editor();editor.setConfig({title:payload});
assert(!editor.shadowRoot.innerHTML.includes(payload));assert(editor.shadowRoot.innerHTML.includes("&quot;"));
card._hass={states:{'notify.external':{attributes:{friendly_name:payload}}},entities:{}};
card._els={dest:{value:"",innerHTML:""}};card._syncDestinations();
assert(!card._els.dest.innerHTML.includes(payload));assert(card._els.dest.innerHTML.includes("&lt;img"));
assert.deepEqual(Array.from(card._notifyEntities()),["notify.external"]); // fallback still includes non-Free entities
console.log("4 frontend probes passed: title, editor, option escaping; broad notify fallback confirmed (fake DOM, not browser).");
