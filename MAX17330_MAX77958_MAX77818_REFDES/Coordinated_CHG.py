import smbus, time, os, _thread



##################### Get keyboard input #####################
import tty, sys, termios
##################### Get keyboard input #####################




from MAX17330 import MAX17330
# TODO Uncomment from MAX77818 import MAX77818
from MAX77958 import MAX77958
import RPi.GPIO as GPIO
bus=smbus.SMBus(1)

# Configure GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
#GPIO.setmode(GPIO.BCM)
Alrt1=13
Alrt2=15
TriggerPin=18  
# PIn that is the interrupt
GPIO.setup(TriggerPin,GPIO.OUT)
GPIO.setup(Alrt1,GPIO.OUT)
GPIO.setup(Alrt2,GPIO.OUT)
GPIO.output(TriggerPin, 0)


sa = 0x36

#initialize new MAX77958 instance and reset all registers
usb=MAX77958()
time.sleep(1)
usb.reset_MAX77958()
time.sleep(2) #wait here to let the MAX77958 reset all registers



# TODO Uncomment m818=MAX77818()


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

'''
# TODO Uncomment 
def initialize_MAX77818(VCHG=3.5):
    m818.set_input_lim(3.0)
    m818.set_cc(3.0)
    m818.set_cv(VCHG)
    m818.set_mode(5)
'''

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

'''
# TODO: configure this function definition to manage how the MAX77958 initializes the charging state        
def manage_charging():
    usb.set_qc9v()
    if chg1.is_dropout() or chg2.is_dropout():
        if m818.get_chg_stat() in [0x2,0x3]:
            print("Stepping voltage up")
            m818.set_cv('up')
        else:
            print("CHG_DETAILS_01 = {}.  Cannot step up voltage".format(hex(m818.get_chg_stat())))
'''

# Function to test the PPS increment voltage functions
def pps_sawtooth_test():
    # print("max pps_voltage = ",usb.pps_voltage_max*20,"mV")
    # print("min pps_voltage = ",usb.pps_voltage_min*20,"mV")
    print("cur pps_voltage = ",usb.pps_voltage*20,"mV")

    pps_ret = 0
    if usb.pps_voltage < usb.pps_voltage_max:
        pps_ret = usb.increment_pps_voltage()
        #print("Stepping voltage up")
    else:
        usb.set_APDO_SrcCap_Request(usb.curr_pdo_src_selected, usb.pps_voltage_min & 0x00ff, ((usb.pps_voltage_min & 0xff00) >> 8),0x00) # Reset voltage back to min APDO PPS Volt ~3.3v
    # print("usb.set_pps return value = {}".format(hex(pps_ret)))
    # print()
    return pps_ret

def alt_qc_test():
    time.sleep(0.1)
    usb.set_qc5v()
    time.sleep(0.1)
    usb.set_qc9v()

def read_all_max77958_interrupts():
    interrupts_ret = []
    interrupts_ret = usb.read_all_int_regs()
    # print("interrupt register read values:")
    # print("{}=\t{}\t{}" .format( hex(0x04), hex(interrupts_ret[0]), bin(interrupts_ret[0]) ))
    # print("{}=\t{}\t{}" .format( hex(0x05), hex(interrupts_ret[1]), bin(interrupts_ret[1]) ))
    # print("{}=\t{}\t{}" .format( hex(0x06), hex(interrupts_ret[2]), bin(interrupts_ret[2]) ))
    # print("{}=\t{}\t{}" .format( hex(0x07), hex(interrupts_ret[3]), bin(interrupts_ret[3]) ))

def read_all_max77958_registers():
    # read all the registers
    all_reg = []
    all_reg = usb.read_reg(0x00,20)
    #print("Register Data")
    for x in range(len(all_reg)):
        print("{}=\t{}\t{}" .format( hex(x), hex(all_reg[x]), bin(all_reg[x]) ))
    return all_reg


#charge_log_1p("trial_BC30_log.csv")
    #Parallel Managed charging, single device charging, direct USB Charging
#reset_to_NVM_SID()

#Change these path names to wherever the files for the batteries are stored
ini1 = '/home/pi/Documents/Codebase/MAX17330_MAX77958_MAX77818_REFDES/2000_mAh_EZ.INI'
ini2 = '/home/pi/Documents/Codebase/MAX17330_MAX77958_MAX77818_REFDES/2500_mAh_EZ.INI'

# TODO Uncomment this is for finding the slave addresses for the MAX17330
'''
fix_sid()
if(0x4b in search_max17330()):
    chg1=MAX17330(sa=0x76)
    chg1.load_RAM_ini(ini1)
if(0x4f in search_max17330()):
    chg2=MAX17330(0x72)
    chg2.load_RAM_ini(ini2)
'''

# usb.set_qc9v()

# TODO Uncomment initialize_MAX77818(max(chg1.get_vcell(),chg2.get_vcell())+0.05)
# TODO Uncomment _thread.start_new_thread(print_details,())

'''
#test PPS mode configuration
returned_set_pps_value = usb.set_pps(0x01, 0xFB, 0x00, 0x00)
print("SET_PPS returned value = ")
print(returned_set_pps_value)
'''

'''
##################### Get keyboard input #####################
filedescriptors = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin)
x = 0
##################### Get keyboard input #####################
'''

#time.sleep(0.25)
GPIO.output(TriggerPin, 1)

time.sleep(0.01)

# unmask all ints
mask = [0b00000000, 0b00000000, 0b00000000, 0b00000000]
usb.write_reg(0x10,mask,4)

time.sleep(0.05)

#read all max77958 registers
# read_all_max77958_registers()
# time.sleep(0.05)

read_all_max77958_interrupts()
time.sleep(0.05)

#configure pdo variables
usb.configure_pdo_src_variables()
time.sleep(0.05)

# find capanle pps devices
pps_pdo_ret = usb.find_pps_capable_pdo()
print("usb.find_pps_capable_pdo return value = ")
print(pps_pdo_ret)

read_all_max77958_interrupts()
time.sleep(0.05)

# TODO make this automatic in a high level function later
# enable PPS mode
pps_ret = usb.set_pps(0x01, 0x2C, 0x01, 0x00) # Enable defualt voltage of 6 volts with no artificial current limit
print("usb.set_pps return value = {}".format(hex(pps_ret)))

read_all_max77958_interrupts()
time.sleep(0.05)

# TODO make this automatic in a high level function later
# enable APDO if there is a PDO object that is PPS compatible with adjustabe voltage
'''
if len(pps_pdo_ret) < 0:
    REQ_APDO_POS = pps_pdo_ret[0]
    print("REQ_APDO_POS value = {}".format(hex(REQ_APDO_POS)))
    apdo_ret = usb.set_APDO_SrcCap_Request(REQ_APDO_POS, usb.pps_voltage_min & 0x00FF, ((usb.pps_voltage_min & 0xff00) >> 8), OPERATING_CURRENT=0x00)
    print("usb.set_APDO_SrcCap_Request return value = {}".format(hex(apdo_ret)))
'''
time.sleep(1)

REQ_APDO_POS = 0x05
#apdo_ret = usb.set_APDO_SrcCap_Request(0x05, (usb.conv_pdo_src_min_voltage[REQ_APDO_POS] & 0x00FF), ((usb.conv_pdo_src_max_voltage[REQ_APDO_POS] & 0xff00) >> 8), OPERATING_CURRENT=0x00)
apdo_ret = usb.set_APDO_SrcCap_Request(0x05, 0xFA, 0x00, OPERATING_CURRENT=0x00)
print("usb.set_APDO_SrcCap_Request return value = {}".format(hex(apdo_ret)))
print("current pdo selected",usb.curr_pdo_src_selected)

read_all_max77958_interrupts()
time.sleep(0.05)

GPIO.output(TriggerPin, 0)
time.sleep(0.01)
GPIO.output(TriggerPin, 1)
time.sleep(0.01)
GPIO.output(TriggerPin, 0)
time.sleep(0.01)
GPIO.output(TriggerPin, 1)
time.sleep(0.01)
GPIO.output(TriggerPin, 0)
time.sleep(0.01)
GPIO.output(TriggerPin, 1)
time.sleep(0.01)



while(1):
    '''
    x=sys.stdin.read(1)[0]
    print("You pressed", x)
    if x == "r":
        print("If condition is met")
    '''
    # TODO UNCOMMENT manage_charging()
    # alt_qc_test()
    pps_sawtooth_test()
    read_all_max77958_interrupts()
    time.sleep(0.01)

#termios.tcsetattr(sys.stdin, termios.TCSADRAIN,filedescriptors)
