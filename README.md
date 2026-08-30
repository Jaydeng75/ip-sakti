# IP-SAKTI

The project is organized into:

- [`frontend/`](frontend/) — Next.js web application
- [`backend/`](backend/) — FastAPI application and backend services

## Frontend development

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in a browser.

## Checks

Run the frontend checks from the `frontend/` directory:

```bash
npm run lint
npm run build
```

## Backend development

Run backend commands from the `backend/` directory:

```bash
cd backend
uvicorn main:app --reload
```

The current backend requires its Python dependencies and PostgreSQL database to
be configured before startup.
