// Login / sign-up: Firebase Auth with Google popup + email/password.
import { getFirebaseAuth, getConfig } from "./firebase-init.js";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  updateProfile,
  onAuthStateChanged,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const $ = (id) => document.getElementById(id);
const errorEl = $("error");
let mode = "signin"; // | "signup"

function setMode(next) {
  mode = next;
  const signup = mode === "signup";
  $("name-field").classList.toggle("hidden", !signup);
  $("kicker").textContent = signup ? "Start your journey" : "Welcome back, traveler";
  $("title").textContent = signup ? "Create your Wanderlore" : "Sign in to Wanderlore";
  $("subtitle").textContent = signup
    ? "One account for every trip you'll dream up."
    : "Pick up your journeys where you left off.";
  $("submit-btn").textContent = signup ? "Create account" : "Sign in";
  $("toggle-line").innerHTML = signup
    ? 'Already exploring? <button id="toggle-btn" type="button">Sign in</button>'
    : 'New to Wanderlore? <button id="toggle-btn" type="button">Create an account</button>';
  $("toggle-btn").addEventListener("click", () => setMode(signup ? "signin" : "signup"));
  errorEl.textContent = "";
}

function friendly(code) {
  return {
    "auth/invalid-credential": "Incorrect email or password.",
    "auth/invalid-email": "That email address looks invalid.",
    "auth/email-already-in-use": "An account already exists for that email.",
    "auth/weak-password": "Password should be at least 6 characters.",
    "auth/too-many-requests": "Too many attempts — please try again later.",
    "auth/popup-closed-by-user": "Google sign-in was cancelled.",
    "auth/operation-not-allowed": "This sign-in method isn't enabled yet in Firebase.",
  }[code];
}

async function main() {
  const cfg = await getConfig();
  if (!cfg.authRequired) {
    window.location.href = "/app.html";
    return;
  }

  const auth = await getFirebaseAuth();
  onAuthStateChanged(auth, (user) => {
    if (user) window.location.href = "/app.html";
  });

  $("toggle-btn").addEventListener("click", () => setMode("signup"));

  $("google-btn").addEventListener("click", async () => {
    errorEl.textContent = "";
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
      window.location.href = "/app.html";
    } catch (err) {
      errorEl.textContent = friendly(err.code) || err.message;
    }
  });

  $("auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.textContent = "";
    const btn = $("submit-btn");
    btn.disabled = true;
    const email = $("email").value.trim();
    const password = $("password").value;
    const name = $("name").value.trim();
    try {
      if (mode === "signup") {
        const cred = await createUserWithEmailAndPassword(auth, email, password);
        if (name) await updateProfile(cred.user, { displayName: name });
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      window.location.href = "/app.html";
    } catch (err) {
      errorEl.textContent = friendly(err.code) || err.message;
    } finally {
      btn.disabled = false;
    }
  });
}

main().catch((e) => {
  errorEl.textContent = "Couldn't initialise sign-in. Is Firebase configured? " + e.message;
});
