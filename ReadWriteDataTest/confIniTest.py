from configobj import ConfigObj
from validate import Validator

cspec = ConfigObj("GPCAlgoConf.spec",list_values=False)
c = ConfigObj("GPCAlgoConf.ini", configspec=cspec)
cv = c.validate(Validator())
print cv
print c
print c.keys()
print c['MPC']['simu']
print type(c['MPC']['simu'])

