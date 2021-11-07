#!/usr/bin/env python
import minimalmodbus

def main():
    try:
        instrument = minimalmodbus.Instrument('/dev/ttyAMA1', 10)

        registers = instrument.read_registers(4114, 29)

        dispavgVbatt = registers[0]/10.0
        dispavgVpv = registers[1]/10.0
        IbattDisplay = registers[2]/10.0
        kWHours = registers[3]/10.0
        watts = registers[4]
        chargeState = registers[5]
        batteryState = (registers[5] & 0xFF00) >> 8
        classicState = registers[5] & 0xFF
        PvInputCurrent = registers[6]/10.0
        VocLastMeasured = registers[7]/10.0
        HighestVinputLog = registers[8]/10.0
        AmpHours = registers[10]
        LifeTimekWHours = registers[11]
        LifetimeAmpHours = registers[12]
        BATTtemperature = registers[17]
        NiteMinutesNoPwr = registers[20]
        FloatTime = registers[23]
        AbsorbTime = registers[24]
        EqualizeTime = registers[28]

        print("solar dispavgVbatt={},dispavgVpv={},IbattDisplay={},kWHours={},watts={},chargeState={},batteryState={},classicState={},PvInputCurrent={},VocLastMeasured={},HighestVinputLog={},AmpHours={},NiteMinutesNoPwr={},FloatTime={},AbsorbTime={},EqualizeTime={}".format(dispavgVbatt,dispavgVpv,IbattDisplay,kWHours,watts,chargeState,batteryState,classicState,PvInputCurrent,VocLastMeasured,HighestVinputLog,AmpHours,NiteMinutesNoPwr,FloatTime,AbsorbTime,EqualizeTime))

    except:
        print("solar dispavgVbatt=,dispavgVpv=,IbattDisplay=,kWHours=,watts=,chargeState=,batteryState=,classicState=,PvInputCurrent=,VocLastMeasured=,HighestVinputLog=,AmpHours=,NiteMinutesNoPwr=,FloatTime=,AbsorbTime=,EqualizeTime=")

if __name__ == '__main__':
    main()

