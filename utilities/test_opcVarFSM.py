""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
"""
Created on 9 oct. 2012
"""
import unittest
from datetime import datetime
from dateutil import tz
from opcVarHandling import opcVar, OPCVarSpecif
OPCVarSpecif['SCADA.S4_QSoll'] = {'NK':2,'Access':'rw'}


class Test(unittest.TestCase):


    def setUp(self):
        self.var = opcVar('SCADA.S4_QSoll',210,'Good','2012-10-09 12:00:00')


    def tearDown(self):
        del(self.var)


    # === Test methods ===

    # === Part reading/set values ===
    def testBase_R_AfterSetup(self):
        self.assertEqual(self.var.name, 'SCADA.S4_QSoll',
                         "SetUp should initialize this variable")
        self.assertTrue(self.var.fsm.QualityState.name() == "UptoDate",
                        "setUp should end up with an up-to-date variable")
        self.assertEqual(self.var.value, 2.1,
                         "S4_QSoll has an NK=2 specification")
    def testUpdateValue_RG(self):
        self.assertEqual(self.var.setValue('SCADA.S4_QSoll', 320, 'Good', '2012-10-09 12:15:00'),None,
                        "Setting a value should return None (no return specified)")
        self.assertTrue(self.var.fsm.QualityState.name() == "UptoDate",
                        "setting a value with quality Good should end up with an up-to-date variable")
        self.assertEqual(self.var.value, 3.2,
                         "S4_QSoll has an NK=2 specification")
        self.assertEqual(self.var.getCached(),
                         ('SCADA.S4_QSoll', 3.2, '2012-10-09 12:15:00', datetime(2012,10,9,12,15,tzinfo=tz.tzutc())),
                          "The default of the get from cach should return the last value set")
        self.assertEqual(self.var.getCached("Latest"),
                         ('SCADA.S4_QSoll',2.1,'2012-10-09 12:00:00',datetime(2012,10,9,12,tzinfo=tz.tzutc())),
                          "The Latest from the cach should return the value set at t-1")
        self.assertEqual(self.var.getDiff().Diff[0], 3.2-2.1,
                         "The Variable should handle the modifications over time")
    def testUpdateValue_RB(self):
        self.assertEqual(self.var.setValue('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:15:00'),None,
                        "Setting a value should return None (no return specified)")
        self.assertTrue(self.var.fsm.QualityState.name() == "FromCach",
                        "setting a value with quality Bad should end up with an variable state that reads from cach")
        self.assertTrue(self.var.usable,
                        "One bad reading is not enough to become unusable.")
        self.assertEqual(self.var.value, 2.1,
                         "The bad quality value should not be returned")
    def testRReset(self):
        self.var.setValue('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:20:00')
        self.var.setValue('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:25:00')
        self.var.setValue('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:30:00')
        self.assertTrue(self.var.fsm.QualityState.name() == "Problem",
                        "setting 3 (default) times a value with quality Bad should end up with an variable state Problem")
        self.var._reset()
        self.testBase_R_AfterSetup()
        self.assertEqual(self.var.setValue('SCADA.S4_QSoll', 320, 'Good', '2012-10-09 12:15:00'),None,
                        "Setting a value should return None (no return specified)")
        self.assertTrue(self.var.fsm.QualityState.name() == "UptoDate",
                        "setting a value with quality Good should end up with an up-to-date variable")
        self.assertEqual(self.var.value, 3.2,
                         "S4_QSoll has an NK=2 specification")
    def testBadSinceStart(self):
        self.var = opcVar('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:15:00')
        self.var.setValue('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:20:00')
        self.var.setValue('SCADA.S4_QSoll', 320, 'Bad', '2012-10-09 12:25:00')
        self.assertTrue(self.var.fsm.QualityState.name() == "Problem",
                        "setting 3 (default) times a value with quality Bad should end up with an variable state Problem")
        self.var._reset()
        self.assertTrue(self.var.fsm.QualityState.name() == "UptoDate",
                        "setUp should end up with an up-to-date variable")
        self.assertEqual(self.var.value, None,
                         "S4_QSoll was never set with Good so its Value is None")

    # === Part opc write process ===
    def testBase_W_AfterSetup(self):
        self.assertTrue(self.var.isWritable(),
                        "The Used Variable should be read/write enabled")
        self.assertTrue(self.var.fsmW.WriteState.name() == "Idle",
                        "setUp should end up with an Idle variable")
    def testSetWriteValueBase(self):
        self.assertEqual(self.var.setWriteValue(1.2), ('SCADA.S4_QSoll',120),
                         "The method to set the write value should return the tuple to be used for OPCwrite (NK converted)")
        self.assertTrue(self.var.isWReady(),
                        "After having set a write value the variable should be in a write-ready state")
    def testWriteOK(self):
        self.testSetWriteValueBase()
        self.var.Write(True)
        self.assertEqual(self.var.fsmW.WriteState.name(), 'Idle',
                         "After a successful write Event the Write FSM should be in state Idle")
        self.assertEqual(self.var.wvalue, None,
                         "After a successful write Event stored write value should return None (no cash)")
        self.assertEqual(self.var.fsmW.data, None,
                         "But also the data stored in the state machine should be None (no cash)")
        self.assertEqual(self.var.value, 1.2,
                         "And the variable read value should have been set to the written value")
    def testWrite_1E_1OK(self):
        self.testSetWriteValueBase()
        self.var.Write(False)
        self.assertEqual(self.var.fsmW.WriteState.name(), 'WritePending',
                         "After a first unsuccessful write Event the Write FSM should still be in state WritePending")
        self.assertEqual(self.var.fsmW.cWError, 1,
                         "After a first unsuccessful write Event the WriteError counter should be incremented")
        self.var.Write(True)
        self.assertEqual(self.var.fsmW.WriteState.name(), 'Idle',
                         "After a successful write Event the Write FSM should be in state Idle")
        self.assertEqual(self.var.fsmW.cWError, 0,
                         "After a second successful write Event the WriteError should be reseted")
        self.assertEqual(self.var.fsmW.data, None,
                         "The data stored in the state machine should be None (no cash)")
        self.assertEqual(self.var.value, 1.2,
                         "And the variable read value should have been set to the written value")
    def testWriteOverwrite(self):
        self.testSetWriteValueBase()
        self.assertEqual(self.var.setWriteValue(1.3), ('SCADA.S4_QSoll',130),
                         "The method should overwrite the write value")
        self.assertEqual(self.var.fsmW.WriteState.name(), 'ToWrite',
                        "But the state machine should stay in ToWrite")
    def testWriteWithCash(self):
        self.var.setWriteValue(1.2,ImplicitTrig=True)
        self.assertEqual(self.var.fsmW.WriteState.name(), 'WritePending',
                         "After Implicit Trigger the Write FSM should be in state WritePending")
        self.assertEqual(self.var.getWCach(), None,
                         "In case of no write value cash the return value should be None")
        self.assertEqual(self.var.setWriteValue(1.3,ImplicitTrig=True), ('SCADA.S4_QSoll',120),
                         "In WritePending state an additional set write value should go to the cash, the return should be the value tuple that will be written first")
        self.assertEqual(self.var.getWCach().value, 1.3,
                         "Now the cashed data should be returned")
        self.var.Write(True)
        self.assertEqual(self.var.value, 1.2,
                         "And the variable read value should have been set to the written value")
        self.assertEqual(self.var.fsmW.WriteState.name(), 'ToWrite',
                         "After a successful write Event the Write FSM should be in state ToWrite (with cash)")
        self.assertEqual(self.var.wvalue, ('SCADA.S4_QSoll',130),
                         "The write value should now be the previous cashed value (NK converted)")
        self.assertEqual(self.var.getWCach(), None,
                         "The cash should be empty now")
        self.var.Write(True)
        self.assertEqual(self.var.value, 1.3,
                         "The variable read value should have been set to the written value")
        self.assertEqual(self.var.fsmW.WriteState.name(), 'Idle',
                         "After a successful write Event the Write FSM should be in state Idle (no cash any more)")


    def testWrite_MaxE(self):
        self.testSetWriteValueBase()
        for i in xrange(self.var.fsmW.cWErrorMax):
            self.var.Write(False)
        self.assertEqual(self.var.fsmW.WriteState.name(), 'Problem',
                         "After Max Error unsuccessful write Event the Write FSM should still be in state Problem")
        self.assertEqual(self.var.value, 2.1,
                         "And the variable read value should still have the old value")
    def testWReset(self):
        self.testWrite_MaxE()
        self.var._reset()
        self.testBase_R_AfterSetup()
        self.testBase_W_AfterSetup()

    # === utility methods ===

    def runScenario(self,scenario):
        for item in scenario:
            pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
