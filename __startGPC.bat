rem batch to only start the "GPC Task" in a dedicated cmd

cd ReadWriteDataTest
del MPCAlgos.Opti_persistent.pkl

color 80
python GPCAlgGlobFSM.py
