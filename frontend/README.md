# FitAI React frontend

Standalone React + Vite frontend for the existing Django FitAI application.

## Run locally

Requirements: Node.js 20.19+ (or 22.12+) and npm.

From PowerShell:

```powershell
cd frontend
$env:VITE_API_BASE_URL = "https://fit-ai-z29o.onrender.com"
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The Django
backend must be running the updated API code and allow the local Vite origin.
The development origin is allowed only when Django `DEBUG` is enabled.

Create and verify a production build:

```powershell
npm run build
npm run preview
```

## Deploy to Vercel

1. Deploy the Django changes to the existing Render service first. The frontend
   depends on the new session endpoints and read-only APIs in that deployment.
2. In Render's environment settings, set `VERCEL_FRONTEND_ORIGIN` to the exact
   deployed Vercel origin, for example `https://your-fitai.vercel.app` (no path
   or trailing slash). Do not use a wildcard. Redeploy Render after setting it.
3. Import the repository into Vercel and set **Root Directory** to `frontend`.
   Vercel will use `npm run build` and `dist` as the output directory.
4. Add the Vercel environment variable `VITE_API_BASE_URL` with the backend
   origin `https://fit-ai-z29o.onrender.com`. This is a public URL, not a
   credential. Do not put API keys or passwords in Vite variables.
5. Deploy or redeploy the Vercel project. `vercel.json` routes browser refreshes
   to the React app entry point.

The backend uses exact-origin CORS with credentials and trusts the configured
origin for CSRF. Production session and CSRF cookies are marked `Secure` and
`SameSite=None` when `VERCEL_FRONTEND_ORIGIN` is configured. Browser privacy
settings that block third-party cookies may still prevent cross-site session
cookies; test sign-in in the target browsers.

## Integration status

- Session login, registration, logout and session checks use Django's existing
  user model and cookie-based authentication.
- Nutrition scans use the existing `/nutrition/scan/` endpoint and may invoke
  the configured AI provider and save a scan when submitted.
- Workout recommendations use a small read-only JSON endpoint; start and
  completion use the existing workout endpoints.
- Progress metrics use a small read-only summary endpoint; updates use existing
  step, goal and weight endpoints.
- The chatbot consumes the existing server-sent event response.
- Diet plan generation/display and reminders remain in their existing
  server-rendered Django pages because they do not have JSON APIs. The React
  pages link to those pages rather than interpreting HTML as JSON.
- AI posture remains the existing camera-enabled HTML page and is opened in a
  separate tab. Camera permissions and external browser dependencies require
  manual browser testing.

The new API code is not available on the deployed Render service until those
Django changes and the CORS dependency are deployed there.
