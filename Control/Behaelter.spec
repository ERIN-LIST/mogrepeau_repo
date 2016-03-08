[Global]
Behaelter = option("Mousel", "Sauer", "Alzette") 
BId = integer(1,51)
DefaultBZ = string(min=4,max=7)
OptionSinkBehaelter = string_set(min=0,max=6)
DailyMeanHorizon = integer(1, 365, default=1) #If specified at basin level it overwrites the global value. This value can be overwritten by the corresponding OPC variables
SPCalcType = integer(1, 2, default=1) #If specified at basin level it overwrites the global value. This value can be overwritten by the corresponding OPC variables

[Betriebszustaende]
[[__many__]]
#Source = option("Provider","Mousel", "Sauer", "Alzette", "")
Source = string_set(min=0,max=20)
Sink   = string_set(min=0,max=20)
Status = option('c','a','o','b')
Vmin   = integer(min=0,max=200)
Vmax   = integer(min=60,max=1000)
