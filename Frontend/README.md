# Vithara Recovery Monitor — Converted Stitch JSX

This folder contains the 19 Google Stitch screens converted from static `code.html` files into React JSX components.

## Run

```bash
npm install
npm run dev
```

Open the local Vite URL. The temporary `App.jsx` shows a screen switcher so you can verify every converted page before adding frontend routing and backend connection.

## Converted pages

- Common: Login, Register
- Patient: PatientDashboard, CaptureWoundPhoto, AIAnalysisResult, RecoveryTrends, Reminders, VoiceAssistant, CareTeam, PatientProfile
- Doctor: DoctorDashboard, PatientRecords, PatientSummary, WoundReview, Appointments, UrgentAlerts, ConsultationSession, DoctorNotifications, DoctorProfile

## Next steps

1. Replace temporary screen switcher with React Router.
2. Add role-based routing.
3. Connect `/auth/login`, `/auth/register`, `/classify`, `/triage`, etc.
