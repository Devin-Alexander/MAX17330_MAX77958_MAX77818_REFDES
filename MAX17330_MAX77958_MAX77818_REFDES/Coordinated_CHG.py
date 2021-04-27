import smbus, time, os, _thread

from MAX17330 import MAX17330
from MAX77818 import MAX77818
from MAX77958 import MAX77958
import RPi.GPIO as GPIO
bus=smbus.SMBus(1)
sa = 0x36
usb=MAX77958()
m818=MAX77818()

GPIO.setmode(GPIO.BOARD)
Alrt1=13
Alrt2=15
GPIO.setup(Alrt1,GPIO.OUT)
GPIO.setup(Alrt2,GPIO.OUT)


def change_SID(sid, gotosid=0,timeout=6,sleep=0.01):
    #GPIO must be managed externally.
    bus.write_word_data(sid,0x61,0)
    bus.write_word_data(sid,0x61,0)
    SID_2={0x36:0x0b,0x72:0x4f,0x32:0x0f,0x76:0x4b}[sid]
    bus.write_word_data(SID_2,0x2b,(gotosid<<4)|1)
    new_sa={0:0x76,1:0x32,2:0x72,3:0x36}[gotosid]
    tstart=time.time()
    while (time.time() - tstart) <timeout:
        try:
            bus.write_quick(new_sa)
            print("Found device at address {}".format(hex(new_sa)))
        except:
            print("No Dev at {}".format(hex(new_sa)))
            time.sleep(sleep)
        try:
            bus.write_quick(sid)
            print("Found device at old address {}".format(hex(sid)))
        except:
            time.sleep(sleep)
    if (time.time() - tstart) >=timeout:
        print("Changing Slave ID timed out")
        return 1
    prev_val = bus.read_word_data(new_sa,0x61)
    val = (prev_val & 0xFF07) | 0xF8
    bus.write_word_data(new_sa,0x61,val)

def search_max17330():
    found_devs=[]
    for addr in [0x4b,0x0f,0x4f,0x0b]: #0x6C-->0x36, 0x16-->0x0b
        try:
            bus.write_quick(addr)
            found_devs.append(addr)
        except:
            pass
    return found_devs

def fix_sid():
    devs=search_max17330()
    if len(devs)<1:
        print("No MAX17330 Secondary slave addresses found.  Exiting fix_sid routine")
        return 0
    if 0x4B in devs:
        print("MAX17330 Device 1 is already at correct slave address")
    elif 0x0b in devs:
        GPIO.output(Alrt1,GPIO.HIGH)
        GPIO.output(Alrt2,GPIO.LOW)
        change_SID(0x36,0)
        if(search_max17330() == devs):
            print("No change after trying to move Device 1.  Check power to Device 1")
        else:
            print("MAX17330 Device 1 moved to SID 0x76, 0x4B")
    devs=search_max17330()
    if 0x4F in devs:
        print("MAX17330 Device 2 is already at correct slave address")
    elif 0x0b in devs:
        GPIO.output(Alrt1,GPIO.LOW)
        GPIO.output(Alrt2,GPIO.HIGH)
        change_SID(0x36,2)
        if(search_max17330() == devs):
            print("No change after trying to move Device 2.  Check power to Device 2")
        else:
            print("MAX17330 Device 2 moved to SID 0x72, 0x4F")

def reset_to_NVM_SID():
    for addr in [0x72,0x32,0x76]:
        try:
            bus.write_word_data(addr,0x60,0x000F)
        except:
            pass

def initialize_MAX77818(VCHG=3.5):
    m818.set_input_lim(3.0)
    m818.set_cc(3.0)
    m818.set_cv(VCHG)
    m818.set_mode(5)

def print_details():
    import sys,time
    while(1):
        time.sleep(1)
        dout = ""
        if chg1 is not None:
            dout+="Device 1:    VCell = {}   IChg = {}   Target = {}    VSYS={} ".format(chg1.get_vcell(),chg1.get_ibatt(),chg1.get_ichg(),chg1.get_vpckp())
        else:
            print("No Chg1")
        if chg2 is not None:
            dout+="Device 2:    VCell = {}   IChg = {}   Target = {}    VSYS={} ".format(chg2.get_vcell(),chg2.get_ibatt(),chg2.get_ichg(),chg2.get_vpckp())
        else:
            print("No Chg1")
        sys.stdout.write(dout + " "*30+ "\r")
        sys.stdout.flush()
# TODO: configure this function definition to manage how the MAX77958 initializes the charging state        
def manage_charging():
    usb.set_qc9v()
    if chg1.is_dropout() or chg2.is_dropout():
        if m818.get_chg_stat() in [0x2,0x3]:
            print("Stepping voltage up")
            m818.set_cv('up')
        else:
            print("CHG_DETAILS_01 = {}.  Cannot step up voltage".format(hex(m818.get_chg_stat())))


#charge_log_1p("trial_BC30_log.csv")
    #Parallel Managed charging, single device charging, direct USB Charging
#reset_to_NVM_SID()

#Change these path names to wherever the files for the batteries are stored
ini1 = '/home/pi/Documents/Codebase/MAX17330_MAX77958_MAX77818_REFDES/2000_mAh_EZ.INI'
ini2 = '/home/pi/Documents/Codebase/MAX17330_MAX77958_MAX77818_REFDES/2500_mAh_EZ.INI'

fix_sid()
if(0x4b in search_max17330()):
    chg1=MAX17330(sa=0x76)
    chg1.load_RAM_ini(ini1)
if(0x4f in search_max17330()):
    chg2=MAX17330(0x72)
    chg2.load_RAM_ini(ini2)
#usb.set_qc9v()
returned_set_pps_value = usb.set_pps(0x02,0xFA, 0x00, 0x00)
initialize_MAX77818(max(chg1.get_vcell(),chg2.get_vcell())+0.05)
_thread.start_new_thread(print_details,())
while(1):
    print("SET_PPS returned value = ")
    print(returned_set_pps_value)

    #manage_charging()
    time.sleep(1)
