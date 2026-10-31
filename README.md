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
