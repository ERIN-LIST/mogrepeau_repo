""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
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

