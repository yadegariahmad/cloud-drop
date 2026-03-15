import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!, {
  onCaughtError: (error) => {
    console.error("React caught error:", error);
  },
  onUncaughtError: (error) => {
    console.error("React uncaught error:", error);
  },
}).render(
  <StrictMode>
    <App />
  </StrictMode>
);
