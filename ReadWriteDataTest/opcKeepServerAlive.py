import OpenOPC
from time import sleep

def main():
    opc = OpenOPC.client()
    opc.connect('OPC.SimaticHMI.CoRtHmiRTm.1')
    while True:
        opcInfo = dict(opc.info())
        ping_f = opc.ping()
        print '{Current Time}: {State} / Ping={PingF} (Startet at: {Start Time})'.format(PingF=ping_f,**opcInfo)
        sleep(2)

if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            sleep(10)
