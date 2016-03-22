# -*- coding: iso-8859-1 -*-
""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

from configobj import ConfigObj
from validate import Validator
from glob import glob



def getKey(bcf,key):
    if isinstance( bcf, dict ):
        if key in bcf.keys():
            if bcf[key] != '':
                return bcf[key]
            else:
                return []
        else:
            ret = []
            for bcfi in bcf.itervalues():
                ret.extend(getKey(bcfi,key))
            return ret
    else:
        return []

B_cf = {}
cspec = ConfigObj("Behaelter.spec",list_values=False)
for fi in glob("Behaelter*.ini"):
    c = ConfigObj(fi, configspec=cspec)
    cv = c.validate(Validator())
    B_cf[c["Global"]["BId"]] = dict(zip(("File","Tree","Valid"),[fi,c,cv]))

print getKey(B_cf,'Source')
print getKey(B_cf,'Sink')
print getKey(B_cf,'Status')
