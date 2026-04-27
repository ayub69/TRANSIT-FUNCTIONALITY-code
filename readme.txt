to run:

python -m uvicorn main:app --reload 
^ will give api screen 
files being used : 
services folder for functioanlity coding

routers for api endpoints

NEW schema was created with valid edges check README_smart_transit3 for it 
python run_main.py --stops ".\graphdata\stops.csv" --order ".\graphdata\route sequence.csv"

Env setup for traffic API:
1) Copy `.env.example` to `.env`
2) Put your real `TOMTOM_API_KEY` in `.env`
3) Restart uvicorn
