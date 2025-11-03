import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { configureApi } from "./api/config";

// Configure API before rendering
configureApi();

createRoot(document.getElementById("root")!).render(<App />);


