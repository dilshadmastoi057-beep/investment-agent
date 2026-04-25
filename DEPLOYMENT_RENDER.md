# Render Deployment

## 1. Push project to GitHub
Create a GitHub repo and push this project.

## 2. Open Render
Go to https://render.com and sign in.

## 3. Create from Blueprint
Choose:
- New +
- Blueprint
- Select your GitHub repo

Render will read `render.yaml` and create:
- `investment-agent-api` as the FastAPI backend
- `investment-agent-web` as the frontend static site

## 4. Important note about the frontend API URL
The frontend is configured to call:

`https://investment-agent-api.onrender.com`

If Render gives your backend a different URL, open the frontend service in Render and update:

`REACT_APP_API_BASE`

Then redeploy the frontend.

## 5. After deployment
Share the frontend link with your supervisor, for example:

`https://investment-agent-web.onrender.com`

## 6. Test
After opening the frontend link:
- Upload `equity_reports_upload_sample.csv`
- Fill the profile form
- Click `Get Recommendation`

## Optional local production build test
From `frontend/web`:

`npm.cmd run build`
