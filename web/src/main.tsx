import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./style.css";
import brandMark from "../../public/assets/liqily-logo.png";

const favicon = document.createElement("link");
favicon.rel = "icon";
favicon.type = "image/png";
favicon.href = brandMark;
document.head.append(favicon);

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
