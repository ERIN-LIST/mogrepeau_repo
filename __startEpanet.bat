rem batch to only start the "GPC Task" in a dedicated cmd

color 4f

rem ## first reset the system
cd .\SimuTestEnv
python resetSystem.py

rem ## than start the epanet task
python RunEpanetTask.py
