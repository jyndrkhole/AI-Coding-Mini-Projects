# NPS Analyst in a Box

Leadership brief for the fictional Future with Shivank Bank survey. NPS, themes, revenue exposure, callbacks, and the alert are calculated in Python. The dashboard and the five specialists read those results. A model is not required.

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

The app is at http://127.0.0.1:5173. Setup, formulas, agent roles, and the API are in `docs/`.

NPS = promoter percentage − detractor percentage. Promoters are 9–10, passives 7–8, detractors 0–6. Expected revenue at risk uses assumed churn of 3%, 10%, and 25%. It is not actual lost revenue. Callback rows are recommendations; the app does not contact customers.

On the supplied file the calculation is July NPS 32.0, August 30.0, September −6.5, and full-period 18.5. The alert is RED because September is below 0 and the drop from July is more than 20 points. OTP and login comments rise with that drop. That is an association in the comments, not proof of cause. Comment volume and expected revenue at risk are ranked separately. Scores that praise the bank but sit at 0–6 are flagged and left unchanged.
