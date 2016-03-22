""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
"""
Created on 12 oct. 2012
"""
import unittest
from ReadData_useOPC import AlgData_OPC

class Test(unittest.TestCase):


    def setUp(self):
        self.ad = AlgData_OPC(variables={"Test":["S0_zLife","S99_zLife"]})


    def tearDown(self):
        del(self.ad)


    def test_readFromOPC_allConfigured(self):
        self.assertEqual(self.ad.readOPC(), None,
                         "If successful the readOPC method should return None")
        self.assertEqual(self.ad.opcVarsDict.keys(),["VictoryClient.S0_zLife","VictoryClient.S99_zLife",],
                         "Only these two are configured in setUp.")

    def test_readFromOPC_someSpecified(self):
        self.assertEqual(self.ad.readOPC(("VictoryClient.S99_zLife",)), None,
                         "If successful the readOPC method should return None")
        self.assertEqual(self.ad.opcVarsDict.keys(),["VictoryClient.S99_zLife",],
                         "Only this one was read after setUp.")
    def test_readFromOPC_getReadValues(self):
        self.ad.readOPC()
        for vi in self.ad.opcVarsDict.itervalues():
            self.assertTrue(vi.usable,"Should be usable")

    def test_writeToOPC_direct(self):
        self.ad.readOPC(("VictoryClient.S99_zLife",))
        zLife = self.ad.opcVarsDict["VictoryClient.S99_zLife"]
        self.assertEqual(self.ad.writeOPC((zLife.name,1), toOPC=True),
                         [(zLife.name,"Success"),],
                         "Should return with success")
        self.assertFalse(zLife.isWReady(),
                         "After writing to the Variable it should be in 'Idle' state")
        afterWrite = zLife.value
        self.ad.readOPC((zLife.name,))
        afterRead = zLife.value
        self.assertEqual(afterWrite, afterRead,
                         "If write process was successful both should be equal")

    def test_writeToOPC_allWritable(self):
        self.ad.readOPC(("VictoryClient.S99_zLife",))
        zLife = self.ad.opcVarsDict["VictoryClient.S99_zLife"]
        self.assertTrue(self.ad.writeOPC((zLife.name,1)),
                        "Should return True as no direct opc write is done")
        self.assertTrue(zLife.isWReady(),
                        "After internal value writing the Variable should be in 'ToWrite' state")
        self.assertEqual(self.ad.writeOPC(allStored=True),
                         [(zLife.name,"Success"),],
                         "Should return with success")
        afterWrite = zLife.value
        self.ad.readOPC((zLife.name,))
        afterRead = zLife.value
        self.assertEqual(afterWrite, afterRead,
                         "If write process was successful both should be equal")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
