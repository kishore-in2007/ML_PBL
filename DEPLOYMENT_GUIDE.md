# 🚀 Vithara Hosting Guide: Vercel & Cloud Backend

This guide outlines how to host the **Vithara Web Application** on **Vercel** with full client-side routing, production asset optimization, and live backend connectivity.

---

## 🏗️ Architecture Overview

The Vithara project consists of two core components:
1. **Frontend (React + Vite + TailwindCSS)**:
   - Hosted on **Vercel** (serverless edge CDN, blazingly fast, global SSL).
2. **Backend (FastAPI + PyTorch/ONNX + SQLite/PostgreSQL)**:
   - Hosted on a Python-compatible cloud host such as **Render**, **Railway**, or **Hugging Face Spaces** using the included `Dockerfile` / `render.yaml`.

---

## ⚡ Option 1: Deploy to Vercel via GitHub (Recommended)

### Step 1: Push latest changes to GitHub
In your terminal, commit and push the newly added hosting configurations:
```bash
git add .
git commit -m "Configure project for Vercel deployment with SPA rewrites and dynamic API base URL"
git push origin main
```

### Step 2: Import Project in Vercel
1. Go to [vercel.com](https://vercel.com) and log in.
2. Click **"Add New..."** ➔ **"Project"**.
3. Select your GitHub repository (`kishore-in2007/ML_PBL` or your fork).
4. Configure Project Settings:
   - **Framework Preset**: `Vite` (automatically detected).
   - **Root Directory**: Click **Edit** and choose `Frontend` *(or leave as `./` since a root `vercel.json` is also provided)*.
   - **Build Command**: `vite build`
   - **Output Directory**: `dist`
5. **Environment Variables**:
   Add the following environment variable:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: URL of your deployed backend (e.g., `https://vithara-backend.onrender.com` or leave empty/local for testing).
6. Click **Deploy**.

---

## 💻 Option 2: Deploy to Vercel via Vercel CLI

If you prefer deploying directly from your local terminal:
```bash
# Install Vercel CLI globally (if not installed)
npm install -g vercel

# Navigate to Frontend directory
cd Frontend

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

---

## 🌐 Backend Hosting (FastAPI + PyTorch ML)

Because the backend uses heavyweight ML libraries (`torch`, `onnxruntime`, `opencv-python`), it is best hosted as a containerized service.

### Quick Deploy to Render:
1. Log in to [render.com](https://render.com).
2. Click **"New +"** ➔ **"Web Service"**.
3. Connect your GitHub repository.
4. Select **Docker** environment:
   - **Dockerfile Path**: `Backend/Dockerfile`
   - **Docker Context**: `Backend`
   - **Plan**: Free or Starter
5. Add Environment Variables:
   - `PORT`: `8000`
   - `DATABASE_URL`: `sqlite:////app/vithara.db`
   - `STORAGE_BACKEND`: `local`
   - `LOCAL_UPLOAD_DIR`: `/app/uploads`
6. Once deployed, copy your Render URL (e.g., `https://vithara-backend.onrender.com`).
7. Paste this URL into your Vercel Project Settings as `VITE_API_BASE_URL`!

---

## 🛠️ What Was Configured for Vercel

1. **SPA Rewrites (`vercel.json`)**: Configured catch-all route rewriting (`/(.*) -> /index.html`) to prevent 404 errors on page reloads across patient and doctor portals.
2. **API Base URL Resolution (`Frontend/src/api/api.js`)**:
   - Fixed hostname detection so public Vercel domains (`*.vercel.app`) don't erroneously append port `:8000`.
   - Priority sequence: `localStorage` override ➔ `VITE_API_BASE_URL` ➔ Capacitor fallback ➔ LAN IP detection ➔ `127.0.0.1:8000`.
3. **Vite React Configuration (`Frontend/vite.config.js`)**: Added standard `@vitejs/plugin-react` config for fast and reproducible cloud builds.
4. **Favicon and Metadata (`Frontend/public/favicon.svg` & `index.html`)**: Added high-resolution SVG favicon, theme color, and SEO description.
5. **Robust Dockerfile (`Backend/Dockerfile`)**: Included `libgl1`, `libglib2.0-0`, and `ffmpeg` dependencies for seamless deployment on Linux cloud containers.
