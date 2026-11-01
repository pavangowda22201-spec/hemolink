# HemoLink — Blood Donor Matching Platform

HemoLink is a blood donor matching platform designed to connect people who need blood with compatible, available donors. The platform includes a FastAPI backend, a React-based hospital dashboard, and an Expo/React Native mobile application.

## Live services

| Component | URL |
|---|---|
| Backend API | https://hemolink-api-tm3c.onrender.com |
| API documentation | https://hemolink-api-tm3c.onrender.com/docs |
| Hospital dashboard | https://hemo-link-dashboard.vercel.app |
| GitHub repository | https://github.com/pavangowda22201-spec/hemolink |

The mobile application is currently distributed as an Android APK.

## Project structure

This repository contains the **HemoLink backend** and its accompanying static interface.

```text
hemolink/
├── app/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── database.py
├── scripts/
│   └── no_show_checker.py
├── static/
│   ├── index.html
│   ├── dashboard.js
│   └── dashboard.css
├── main.py
├── requirements.txt
└── README.md
```

The React/Vite hospital dashboard and Expo mobile application are maintained as separate projects.

## Technology stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, SQLAlchemy
- **Authentication:** JWT
- **Mobile:** React Native, Expo
- **Hospital dashboard:** React, Vite
- **Backend hosting:** Render
- **Dashboard hosting:** Vercel

## Backend — local setup

### Requirements

Install the following:

- Python 3.10 or newer
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone https://github.com/pavangowda22201-spec/hemolink.git
cd hemolink
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database named `hemolink`, or use an existing PostgreSQL instance.

Example:

```sql
CREATE DATABASE hemolink;
```

Configure the database connection using the `DATABASE_URL` environment variable.

Example:

```text
postgresql://USERNAME:PASSWORD@HOST:5432/hemolink
```

Use your actual PostgreSQL credentials. Do not commit database passwords or production credentials to GitHub.

### 5. Configure environment variables

The backend uses the following environment variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes for production | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes for production | Strong secret used for JWT authentication |
| `JWT_EXPIRE_MINUTES` | No | JWT expiration time in minutes; defaults to 1440 |

For a temporary Windows PowerShell session:

```powershell
$env:DATABASE_URL="postgresql://USERNAME:PASSWORD@HOST:5432/hemolink"
$env:JWT_SECRET_KEY="YOUR_LONG_RANDOM_SECRET"
$env:JWT_EXPIRE_MINUTES="1440"
```

Generate and use a strong, private JWT secret in production. Never publish it in this README or commit it to the repository.

### 6. Start the backend

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The local API will be available at:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs

## Backend deployment — Render

The production backend is hosted on Render.

To deploy your own instance:

1. Push the backend repository to GitHub.
2. Open the Render dashboard.
3. Create a new **Web Service**.
4. Connect the HemoLink GitHub repository.
5. Configure the service as follows.

| Setting | Value |
|---|---|
| Runtime | Python |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

### Render environment variables

Add these under the Render service's Environment settings:

```text
DATABASE_URL=your_postgresql_connection_string
JWT_SECRET_KEY=your_strong_random_secret
JWT_EXPIRE_MINUTES=1440
```

Use a PostgreSQL database accessible to the Render service. Make sure the database schema is initialized using the setup process required by the backend before relying on the service.

After deployment, test:

```text
https://YOUR-RENDER-SERVICE.onrender.com/docs
```

### No-show checker — background worker

The repository also contains:

```text
scripts/no_show_checker.py
```

This is a separate background process that checks overdue donor acceptances and no-show conditions.

If this functionality is required in production, deploy it as a separate **Render Background Worker**, using the same repository and required environment variables.

Start command:

```bash
python scripts/no_show_checker.py
```

Do not use the background worker command as the Web Service start command. The API server and background worker are separate processes.

## Hospital dashboard — Vercel

The React/Vite hospital dashboard is maintained separately from this backend repository.

Production dashboard:

https://hemo-link-dashboard.vercel.app

For a separate dashboard deployment:

1. Open Vercel.
2. Import the dashboard's own GitHub repository.
3. Select the Vite framework preset.
4. Configure the dashboard's API base URL to point to the deployed HemoLink backend.
5. Add any required environment variables in Vercel.
6. Deploy and verify that the dashboard can communicate with the backend.

The dashboard's source code and build settings belong to its separate project.

## Mobile application — Expo / React Native

The HemoLink Android application is maintained in a separate Expo project.

The mobile application communicates with the backend through its configured API base URL.

For local development, install the project dependencies:

```bash
npm install
```

Start the Expo development server:

```bash
npx expo start
```

To run on a connected Android development device:

```bash
npx expo run:android
```

Release builds should be generated using the build configuration maintained in the mobile project.

The Android application is currently distributed as an APK rather than through the Google Play Store.

## API overview

The backend provides the services used by the HemoLink platform, including:

- User authentication and account management
- Donor profiles and donor information
- Blood-group compatibility checks
- Donor search and matching
- Emergency blood request management
- Donor acceptance and response tracking
- Hospital-side request management
- Donor reliability and no-show handling
- Location and request-related services

For the current API routes and request/response schemas, refer to the automatically generated Swagger documentation:

https://hemolink-api-tm3c.onrender.com/docs

## Security and deployment notes

- Never commit `.env` files, database passwords, JWT secrets, access tokens, or private credentials.
- Use a strong production `JWT_SECRET_KEY`.
- Restrict database access to trusted services.
- Configure CORS for the actual frontend origins that need API access.
- Keep the API, dashboard, mobile application, and background worker configurations separate.
- Verify environment variables after every deployment.
- Test authentication and critical API workflows after deploying changes.

## Useful commands

| Task | Command |
|---|---|
| Install Python dependencies | `pip install -r requirements.txt` |
| Start local API | `uvicorn main:app --reload` |
| Start production API | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Start no-show worker | `python scripts/no_show_checker.py` |
| Install mobile dependencies | `npm install` |
| Start Expo | `npx expo start` |
| Run Android development build | `npx expo run:android` |

---

**HemoLink — Connecting blood donors with people who need them.**
 

## Complete Deployment Guide — HemoLink

This guide explains how to deploy, configure, connect, verify, and maintain HemoLink. It is intended for developers taking over the project.

## 1. Production architecture

| Component | Technology | Hosting |
|---|---|---|
| Backend API | Python, FastAPI | Render |
| Database | PostgreSQL | Render PostgreSQL or compatible PostgreSQL host |
| Hospital dashboard | React, Vite | Vercel |
| Android application | React Native, Expo | APK distribution |
| Background processing | Python worker | Render Background Worker |

### Production URLs

- Backend: https://hemolink-api-tm3c.onrender.com
- API documentation: https://hemolink-api-tm3c.onrender.com/docs
- Hospital dashboard: https://hemo-link-dashboard.vercel.app
- Backend GitHub: https://github.com/pavangowda22201-spec/hemolink

The dashboard and mobile application are maintained separately from this backend repository.

## 2. Backend deployment — Render

### Prerequisites

- GitHub account with repository access
- Render account
- Python 3.10+
- PostgreSQL database

### Create the backend service

1. Sign in to https://render.com.
2. Select **New → Web Service**.
3. Connect the GitHub repository:
   `pavangowda22201-spec/hemolink`
4. Select the `main` branch.
5. Configure the service:

| Setting | Value |
|---|---|
| Runtime | Python |
| Root Directory | Repository root |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

6. Select the required service plan.
7. Add the environment variables below.
8. Click **Deploy Web Service**.
9. Check the deployment logs for errors.

### Backend environment variables

Configure these in Render → Backend Service → Environment.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Private JWT signing secret |
| `JWT_EXPIRE_MINUTES` | JWT token lifetime; default is 1440 minutes |

Example format:

```env
DATABASE_URL=postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
JWT_EXPIRE_MINUTES=1440
```

Replace example values with the actual production values. Never commit credentials or secrets to GitHub.

**Security:** The development fallback JWT secret in the source code must not be used in production. Always configure a strong private production secret.

### Verify the backend

Open:

- https://hemolink-api-tm3c.onrender.com
- https://hemolink-api-tm3c.onrender.com/docs

Confirm that the service responds and Swagger documentation loads.

## 3. PostgreSQL database setup

1. Sign in to Render.
2. Select **New → PostgreSQL**.
3. Create a database for HemoLink.
4. Choose a region compatible with the backend service.
5. Wait until the database is available.
6. Copy the appropriate database connection string.
7. Add it to the backend's `DATABASE_URL` environment variable.
8. Redeploy the backend if necessary.

Example connection format:

```text
postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE
```

### Database safety

The backend uses SQLAlchemy and creates model tables through `Base.metadata.create_all()` during startup. The current startup code also runs specific schema helper functions.

Not every schema helper in the database module is automatically executed. Before deploying database-changing code:

- Back up the production database.
- Review the required schema changes.
- Confirm that the existing schema is compatible.
- Apply any required migrations safely.
- Test the application before using production data.

Never reset, drop, or recreate the production database as a routine deployment step.

## 4. Hospital dashboard deployment — Vercel

The hospital dashboard is a separate React/Vite project.

Production URL:

https://hemo-link-dashboard.vercel.app

### Deployment procedure

1. Sign in to https://vercel.com.
2. Import the dashboard's GitHub repository.
3. Select the correct production branch.
4. Select the Vite framework preset if detected.
5. Set the Root Directory to the dashboard project directory.
6. Confirm the build command and output directory against the dashboard's `package.json` and Vite configuration.
7. Configure the dashboard's API base URL to use:

```text
https://hemolink-api-tm3c.onrender.com
```

8. Add any required environment variables using the exact names expected by the dashboard source.
9. Deploy the project.
10. Open the deployed dashboard and test its connection to the backend.

**Important:** The dashboard repository's exact environment-variable names, Root Directory, build command, and output directory must be verified in its own source and Vercel settings. Do not guess these values.

## 5. Backend CORS configuration

The backend currently allows the following dashboard origins:

```text
https://hemo-link-dashboard.vercel.app
https://hemo-link-dashboard-fue4cgdlx-pavangowda22201-spec.vercel.app
https://hemolink-dashboard.onrender.com
```

Local development origins are also configured in `main.py` on ports 5173, 5174, 5175, and 5176.

If the dashboard domain changes:

1. Update the backend CORS allow-list.
2. Commit the backend change.
3. Redeploy the backend.
4. Test dashboard API requests again.

Do not use unrestricted CORS settings as a production workaround.

## 6. Android application deployment — Expo

The mobile application is maintained in a separate Expo / React Native project.

Known project information:

| Setting | Value |
|---|---|
| Android application ID | `com.pavanmahesh131313.HemoLinkMobile` |
| Expo project ID | `1a40cd2d-6e69-4770-acd0-146a5ca89712` |
| Expo SDK | 57 |
| API base URL | `https://hemolink-api-tm3c.onrender.com` |
| Distribution | Android APK |

### Local development

Install Node.js and the project dependencies.

```bash
npm install
npx expo start
```

For a connected Android development device:

```bash
npx expo run:android
```

### Release APK

Use the Expo Application Services configuration belonging to the mobile project.

Before creating a release:

1. Inspect `app.json` or `app.config.*`.
2. Inspect `eas.json`.
3. Confirm the Android application ID.
4. Confirm the production API base URL.
5. Confirm the Expo account and project ownership.
6. Confirm the intended EAS build profile.
7. Build the Android APK using the verified profile.
8. Install and test the APK on a physical Android device.

The exact EAS build profile must be checked in the mobile repository before running the release command. Do not invent a profile or expose signing credentials.

The current distribution method is APK sharing; Google Play Store publication is not part of this deployment process.

## 7. Background worker — No-show checker

The backend repository contains:

```text
scripts/no_show_checker.py
```

This is a separate background process. It must not replace the FastAPI Web Service start command.

If automated no-show processing is required:

1. Open Render.
2. Select **New → Background Worker**.
3. Connect the same backend repository.
4. Select the production branch.
5. Set the build command:

```bash
pip install -r requirements.txt
```

6. Set the start command:

```bash
python scripts/no_show_checker.py
```

7. Configure the required database and application environment variables.
8. Deploy the worker.
9. Check worker logs and confirm it remains healthy.

The script's existence in the repository does not prove that a production worker is currently deployed. Confirm its status in Render.

## 8. Deployment order

For a new production environment, follow this order:

1. Create PostgreSQL.
2. Configure database access.
3. Deploy the backend API.
4. Verify backend health and API documentation.
5. Deploy the hospital dashboard.
6. Verify dashboard-to-backend communication.
7. Configure and build the Android APK.
8. Install and test the APK.
9. Deploy the background worker if required.
10. Complete the production verification checklist.

## 9. Production verification checklist

After deployment, verify the following:

- [ ] Backend service is healthy on Render.
- [ ] Swagger documentation opens.
- [ ] PostgreSQL connection works.
- [ ] Authentication works with a dedicated test account.
- [ ] Donor profile retrieval works.
- [ ] Compatible blood groups can be matched.
- [ ] Incompatible blood groups are rejected.
- [ ] Test blood requests can be created.
- [ ] Donor acceptance and arrival workflow works.
- [ ] Dashboard can communicate with the backend.
- [ ] Mobile APK installs and communicates with the backend.
- [ ] Location and tracking workflows work with test accounts.
- [ ] Background worker is healthy if deployed.
- [ ] Database backup and recovery procedures are documented.

Use test accounts and test requests. Never conduct destructive tests against real emergency requests or donor data.

## 10. Troubleshooting

| Problem | What to check |
|---|---|
| Backend deployment fails | Render build logs, Python dependencies, start command |
| Backend cannot connect to database | `DATABASE_URL`, database availability, credentials |
| Authentication fails | JWT secret, token expiration, API response |
| Dashboard API requests fail | API base URL, CORS allow-list, Vercel environment variables |
| Mobile app cannot connect | Production API URL, network connection, backend health |
| Worker stops | Render worker logs, environment variables, database connectivity |
| Database schema errors | Existing schema, startup helpers, required migrations |

Do not solve production issues by deleting user data, resetting the database, or changing unrelated application features.

## 11. Maintenance and future releases

### Backend

1. Make and review changes in the backend repository.
2. Test locally.
3. Commit and push to the configured production branch.
4. Monitor the Render deployment.
5. Check logs and API health.

### Dashboard

1. Make and review changes in the dashboard project.
2. Test the production API connection.
3. Push to its configured production branch.
4. Monitor the Vercel deployment.
5. Verify the live dashboard.

### Mobile

1. Make and review changes in the Expo project.
2. Test on a physical Android device.
3. Confirm API configuration.
4. Build a new APK using the verified EAS profile.
5. Distribute and test the release APK.

### Production security

- Never commit `.env` files or credentials.
- Never publish database passwords, JWT secrets, access tokens, or signing keys.
- Use role-based access for Render, Vercel, Expo, and GitHub.
- Back up the production database before schema changes.
- Keep production and development configuration separate.
- Review logs after every deployment.

## 12. Final handover information

A new developer taking ownership must receive appropriate access to:

- GitHub backend repository.
- Separate dashboard repository.
- Separate mobile application repository.
- Render backend service.
- Render PostgreSQL database.
- Render background worker, if deployed.
- Vercel dashboard project.
- Expo/EAS project.

Confirm the actual service names, repository links, deployment settings, secrets ownership, and backup procedures directly with the project owner.

**Never store passwords, private API keys, signing credentials, or production secrets in this README.**

---

**HemoLink — Connecting compatible blood donors with people who need them.**
