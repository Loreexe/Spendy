import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";
import "./styles/empty-state.css";
import { applyTheme, getInitialTheme, watchSystemTheme } from "./theme";

applyTheme(getInitialTheme());
watchSystemTheme();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
