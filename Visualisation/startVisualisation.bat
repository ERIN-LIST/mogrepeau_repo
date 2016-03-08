@ping 127.0.0.1 -n 2 -w 1000 > nul

start "PVB_Daemon OPC XML-DA" daemon\bin\opcxmlda_client.exe http://localhost/opcxmlda/OPC.SimaticHMI.CoRtHmiRTm.1 Run -itemlist=daemon\bin\GPCVar.list -debug

cd target\release
start "PVB_Server" visualisation.exe
