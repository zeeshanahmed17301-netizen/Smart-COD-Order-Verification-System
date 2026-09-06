# Risk-Guard COD Verification Engine

Risk-Guard is a cash-on-delivery risk engine and verification platform tailored for the Pakistani e-commerce market. It provides ML and rules-based risk scoring with a multi-step automated WhatsApp chatbot integration.

## Architecture
- **Backend**: Django 5 + Django REST Framework + Celery
- **Database**: PostgreSQL (Orders, Enrichments, Outcomes)
- **Cache / Broker**: Redis (for Celery tasks)
- **Frontend**: React + Vite + TailwindCSS 
- **AI/Chatbot**: DeepSeek LLM over OpenAI API standard + Twilio WhatsApp API

## Running The Project Locally

### 1. Requirements
Ensure you have the following installed on your machine:
- Python 3.10+
- Node.js 18+
- PostgreSQL
- Redis Server (Must be running for Celery)

### 2. Backend Setup
Open a terminal and navigate to the backend directory:

```bash
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt

# Run migrations to update the DB schema
python manage.py migrate

# Create a superuser
python manage.py createsuperuser
```

### 3. Environment Variables
Create a `.env` file in the `backend/` folder. Example:
```ini
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=risk_guard
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_NUMBER=+14155238886

DEEPSEEK_API_KEY=your-apikey
DEEPSEEK_BASE_URL=https://api.deepseek.com

CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CHATBOT_NO_REPLY_TIMEOUT_HOURS=5
```

### 4. Running Backend Services

You will need **three terminal windows** for the backend to run everything correctly:

**Terminal 1: Django Server**
```bash
cd backend
.venv\Scripts\activate
python manage.py runserver 8000
```

**Terminal 2: Celery Worker (Processes Tasks)**
```bash
cd backend
.venv\Scripts\activate
celery -A config worker -l info --pool=solo 
# Note: --pool=solo is recommended on Windows to avoid process spawning issues
```

**Terminal 3: Celery Beat (Schedule Background Tasks)**
```bash
cd backend
.venv\Scripts\activate
celery -A config beat -l info
```

### 5. Frontend Setup

Open another terminal for the React frontend:

```bash
cd frontend
npm install

# Start Vite dev server
npm run dev
```
The React frontend should now be running on `http://localhost:5173`.
