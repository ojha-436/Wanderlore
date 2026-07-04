// Loads non-secret Firebase web config from the backend and initialises Auth.
// The web API key is a public identifier — safe to expose to the browser.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

let _config = null;
let _auth = null;

export async function getConfig() {
  if (!_config) {
    const res = await fetch("/api/config");
    if (!res.ok) throw new Error("Failed to load app config");
    _config = await res.json();
  }
  return _config;
}

export async function getFirebaseAuth() {
  if (_auth) return _auth;
  const cfg = await getConfig();
  const app = initializeApp(cfg.firebase);
  _auth = getAuth(app);
  return _auth;
}
