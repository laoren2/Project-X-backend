# Project-X-backend
This FastAPI server backend is built for sportsx app, with pg and redis as database.

How to build?
step1: Clone the code
step2: configure .env file
step3: run "pip install -r requirements.txt"
step4: run "alembic upgrade head" to update db
step5: run "docker-compose -f docker-compose.yml -f docker-compose.override.dev.yml up" to start the backend service