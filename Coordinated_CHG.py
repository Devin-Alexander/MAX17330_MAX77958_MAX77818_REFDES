# Variables used to determine the state of which the program uses to run 
parallel_charging = 0

import smbus, time, os, _thread
##################### Get keyboard input #####################
# TODO remove
import tty, sys, termios
##################### Get keyboard input #####################

from MAX17330 import MAX17330
from MAX77958 import MAX77958

import RPi.GPIO as GPIO
bus=smbus.SMBus(1)

# Configure GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
#GPIO.setmode(GPIO.BCM)
Alrt1=13
Alrt2=15

GPIO.setup(Alrt1,GPIO.OUT)
GPIO.setup(Alrt2,GPIO.OUT)

# initial slave address of the MAX17730
sa = 0x36

#initialize new MAX77958 instance and reset all registers
usb=MAX77958()

# to reset the MAX77958 upon running the program uncomment these lines back in 
time.sleep(1.5)
usb.reset_MAX77958()
time.sleep(3) #wait here to let the MAX77958 reset all registers
# TODO figure out the minimum time needed to reset the MAX77958 and set it to this time instead of 4.5 seconds


# Changes SID of MAX17330
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


# Search for compatible MAX17330s
def search_max17330():
    found_devs=[]
    for addr in [0x4b,0x0f,0x4f,0x0b]: #0x6C-->0x36, 0x16-->0x0b
        try:
            bus.write_quick(addr)
            found_devs.append(addr)
        except:
            pass
    return found_devs


# Fixes Slave Addresses on the MAX17330's 
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
    

# Resets NVM SID
def reset_to_NVM_SID():
    for addr in [0x72,0x32,0x76]:
        try:
            bus.write_word_data(addr,0x60,0x000F)
        except:
            pass


# copied over from MAX17330_log_data.py
def _read_log_line(dev,max_tries=10):
    from datetime import datetime
    data=dev.read_line()
    timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    return timestamp + ',' + ','.join(map(hex,data))

# copied over from MAX17330_log_data.py
def data_log(dev, path, interval=10):
    from datetime import datetime
    import traceback

    if not os.path.exists(path):
        outfile = open(path, 'wb')
        outfile.write("Time,".encode("utf-8") + ",".join(dev.reg_list()).encode("utf-8") + '\n'.encode("utf-8")) # This line was changed to make it compatible with python 3
        outfile.flush()
    else:
        outfile = open(path, 'ab')

    with outfile:
        print("Logging to %s" % os.path.abspath(path))
        last_log = time.clock()
        last_flush = time.clock()
        while True:
            try:
                line = _read_log_line(dev)
                outfile.write(line.encode("utf-8") + '\n'.encode("utf-8")) # This line was changed to make it compatible with python 3
                if time.clock() > last_flush+60:
                    outfile.flush()
                    #os.fsync(outfile.fileno())
                #manage_charging()
                time.sleep(max(0, interval - (time.clock() - last_log)))
                last_log = time.clock()
            except KeyboardInterrupt:
                print("User stopped logging.")
                return
            except IOError as e:
                print((datetime.now().strftime('[%x %X] ') + 
                       'IOError: %s. Logging resumed.' % e))
            except:
                print(traceback.format_exc())


# Prints off data over the serial terminal to monitor some of the regester settings in live time
def print_details():
    import sys,time
    while(1):
        time.sleep(1)
        dout = ""
        if chg1 is not None:
            dout+="Device 1:    VCell = {}   IChg = {}   Target = {}    VSYS={} ".format(chg1.get_vcell(),chg1.get_ibatt(),chg1.get_ichg(),chg1.get_vpckp())
        else:
            print("No Chg1")
        # only run if program set to parallel charging mode
        if parallel_charging is 1:
            if chg2 is not None:
                dout+="Device 2:    VCell = {}   IChg = {}   Target = {}    VSYS={} ".format(chg2.get_vcell(),chg2.get_ibatt(),chg2.get_ichg(),chg2.get_vpckp())
            else:
                print("No Chg2")
        sys.stdout.write(dout + " "*30+ "\r")
        sys.stdout.flush()

# Funciton for checking if battery is in dropout when only charging one battery
def check_single_dropout():
    dropout = chg1.is_dropout()
    usb.pps_voltage_max = 0x00FA # Max output is 5V for a single cell Li+ battery
    # only enter if the MAX17330 reports dropout mode
    if dropout: #  or chg2.is_dropout():
        # check and see if pps voltage is above the max allowed level
        # if array_idx == 0:
        if usb.pps_voltage < usb.pps_voltage_max:
            # if the difference in the charging current is less than 20 mA of the target when the measurement is made, dont increase voltage
            if chg1.get_ibatt() - chg1.get_ichg() < -20: 
                usb.increment_pps_voltage()
                print("Stepping voltage up")
            else:
                print("Dropout detected, but not low enough to warrant voltage increase")
            print("cur pps_voltage = ",usb.pps_voltage*20,"mV")
    return


# Funciton for checking if battery is in dropout when only charging one battery
def check_single_dropout():
    dropout = chg1.is_dropout()
    usb.pps_voltage_max = 0x00FA # Max output is 5V for a single cell Li+ battery
    # only enter if the MAX17330 reports dropout mode
    if dropout: #  or chg2.is_dropout():
        # check and see if pps voltage is above the max allowed level
        # if array_idx == 0:
        if usb.pps_voltage < usb.pps_voltage_max:
            # if the difference in the charging current is less than 20 mA of the target when the measurement is made, dont increase voltage
            if chg1.get_ibatt() - chg1.get_ichg() < -20: 
                usb.increment_pps_voltage()
                print("Stepping voltage up")
            else:
                print("Dropout detected, but not low enough to warrant voltage increase")
            print("cur pps_voltage = ",usb.pps_voltage*20,"mV")
    return


# This function handles calls to other functions to help manage charging of one or two batteries
def manage_charging_parallel():
    # Indicate charger presense to all batteries (even blocked batteries)
    chg1.allow_chg_b()
    if parallel_charging is 1:     # only run if program set to parallel charging mode
        chg2.allow_chg_b()

    # Determine which batteries to block-discharge, to avoid cross-charging
    # (Allow discharging if the low battery is much lower than the full battery) or (the low battery is below VSys_Min)
    if parallel_charging is 1:    # only run if program set to parallel charging mode
        check_battery_voltage_and_disable_parallel_discharging()

    # Consider FET heat: (DC-DC voltage down) 
    check_temperature()
    
    # Consider dropout: (DC-DC voltage up)
    if parallel_charging is 1:    # only run if program set to parallel charging mode
        check_parallel_dropout()
    else:
        check_single_dropout()
    return


def check_parallel_dropout():
    # Consider dropout: (DC-DC voltage up) 
    usb.pps_voltage_max = 0x00FA # Max output is 5V for a single cell Li+ battery
    # only enter if the MAX17330 reports dropout mode
    if chg1.is_dropout() or chg2.is_dropout(): #  or chg2.is_dropout():
        # check and see if pps voltage is above the max allowed level
        # if array_idx == 0:
        if usb.pps_voltage < usb.pps_voltage_max:
            # if the difference in the charging current is less than mA_threshold_from_charging_target specified below in mA of the target when the measurement is made, dont increase voltage
            mA_threshold_from_charging_target = -20 #use a negative number here. 15-40mA seems to be a good number to prevent raising the PPS voltage too fast
            if chg1.get_ibatt() - chg1.get_ichg() < mA_threshold_from_charging_target: 
                usb.increment_pps_voltage()
                print("Stepping voltage up")
            elif chg2.get_ibatt() - chg2.get_ichg() < mA_threshold_from_charging_target: 
                usb.increment_pps_voltage()
                print("Stepping voltage up")
            else:
                print("Dropout detected, but not low enough to warrant voltage increase")

            print("cur pps_voltage = ",usb.pps_voltage*20,"mV")
    return


# Purpose of this function is to initialize a pps voltage right at the program bootup to roughly 40-60mV above the highest vcell battery range
def initialize_good_pps_voltage():
    # print off starting information about the battery and the pps voltage
    print("FUNCTION initialize_good_pps_voltage started")
    
    vcell_1 = chg1.get_vcell()*1000
    print("curr pps_voltage = ",usb.pps_voltage*20.0,"mV")
    print("curr vcell_1 = ",vcell_1,"mV")
    #  only print off the vcell_2 voltage if program set to PARALLEL charging mode
    if parallel_charging is 1:
        vcell_2 = chg2.get_vcell()*1000
        print("curr vcell_2 = ",vcell_2,"mV")

    # this is set to 1 when we want to break out of the while loop
    good_pps_voltage = 0

    while good_pps_voltage == 0:
        # run this branch of logic if program set to SINGLE charging mode
        if parallel_charging is 0:
            vcell_1 = chg1.get_vcell()*1000
            if usb.pps_voltage*20.0 < vcell_1:
                usb.increment_pps_voltage()
                print("Stepping voltage up: curr pps_voltage = ",usb.pps_voltage*20,"mV")
            else:
                good_pps_voltage = 1
        #  run this branch of logic if program set to PARALLEL charging mode
        elif parallel_charging is 1:
            vcell_1 = chg1.get_vcell()*1000
            vcell_2 = chg2.get_vcell()*1000
            if usb.pps_voltage*20.0 < vcell_1:
                usb.increment_pps_voltage()
                print("Stepping voltage up: curr pps_voltage = ",usb.pps_voltage*20,"mV")
            elif usb.pps_voltage*20.0 < vcell_2:
                usb.increment_pps_voltage()
                print("Stepping voltage up: curr pps_voltage = ",usb.pps_voltage*20,"mV")
            else:
                good_pps_voltage = 1
        # time.sleep(0.05) # small delay to see that it is finding a good starting position for the charging
    # Last we run this incrementing command 2 times to give us 2 times 20mV (40mV total) of headroom over the initial voltage of the highest vcell
    usb.increment_pps_voltage()
    print("Stepping voltage up: curr pps_voltage = ",usb.pps_voltage*20,"mV")
    usb.increment_pps_voltage()
    print("Stepping voltage up: curr pps_voltage = ",usb.pps_voltage*20,"mV")    
    print("FUNCTION initialize_good_pps_voltage completed")
    return 


# TODO implement function that checks the voltage of both batteries and enables/disables charging them if difference in Vcell is > 400mV
def check_battery_voltage_and_disable_parallel_discharging():
    # This function will need to be modified when more than two batteries and MAX17330 are present
    vcell_1 = chg1.get_vcell()*1000
    vcell_2 = chg2.get_vcell()*1000
    if vcell_1 > vcell_2 and vcell_1 > vcell_2 + 400 and chg1.crosscharge_enabled == 0:
        # TODO chg1.set_par_en_bit(1)
        print("Battery voltage of battery 1 is 400mV greater than battery 2, disabling the parallel discharging in battery 1")
    elif vcell_2 > vcell_1 and vcell_2 > vcell_1 + 400 and chg2.crosscharge_enabled == 0:
        # TODO chg2.set_par_en_bit(1)
        print("Battery voltage of battery 2 is 400mV greater than battery 1, disabling the parallel discharging in battery 2")
    #else:
        # TODO chg1.set_par_en_bit(0)
        # TODO chg2.set_par_en_bit(0)
    return


# Function that checks if the temperature of the fets is too hot
# The purpose is to lower pps voltage if the temp is above threshold
# Take immediate action to lower it from using CP or CT in ChgStat and lower by 5 * 20mV steps
def check_temperature(): 
    if chg1.is_cp_event():
        print("Battery 1 is too hot, lowering the pps voltage by 100mv")
        lower_pps_voltage_by_100mV()
    elif chg1.is_ct_event():
        print("FET 1 is too hot, lowering the pps voltage by 100mv")
        lower_pps_voltage_by_100mV()
    # only run if program set to parallel charging mode
    if parallel_charging is 1:
        if chg2.is_cp_event():
            print("Battery 2 is too hot, lowering the pps voltage by 100mv")
            lower_pps_voltage_by_100mV()
        elif chg2.is_ct_event():
            print("FET 2 is too hot, lowering the pps voltage by 100mv")
            lower_pps_voltage_by_100mV() 
    return 0


# Helper function used by check_temperature() 
def lower_pps_voltage_by_100mV():
    for x in range(0, 4):
        usb.decrement_pps_voltage()
        print("Stepping voltage down: curr pps_voltage = ",usb.pps_voltage*20,"mV")    
    return


# Function to test the PPS increment voltage functions 
def pps_sawtooth_test():
    usb.pps_voltage_max = 0x00FA # Max output is 5V
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


# TODO remove this as it is not needed in final program
# test to alternate QC charging modes
def alt_qc_test():
    time.sleep(0.1)
    usb.set_qc5v()
    time.sleep(0.1)
    usb.set_qc9v()


# For debugging purposes, uncomment out the following lines in this function
def read_all_max77958_interrupts():
    interrupts_ret = []
    interrupts_ret = usb.read_all_int_regs()
    # print("interrupt register read values:")
    # print("{}=\t{}\t{}" .format( hex(0x04), hex(interrupts_ret[0]), bin(interrupts_ret[0]) ))
    # print("{}=\t{}\t{}" .format( hex(0x05), hex(interrupts_ret[1]), bin(interrupts_ret[1]) ))
    # print("{}=\t{}\t{}" .format( hex(0x06), hex(interrupts_ret[2]), bin(interrupts_ret[2]) ))
    # print("{}=\t{}\t{}" .format( hex(0x07), hex(interrupts_ret[3]), bin(interrupts_ret[3]) ))


# TODO remove this: For debugging purposes
def read_all_max77958_registers():
    # read all the registers
    all_reg = []
    all_reg = usb.read_reg(0x00,20)
    #print("Register Data")
    for x in range(len(all_reg)):
        print("{}=\t{}\t{}" .format( hex(x), hex(all_reg[x]), bin(all_reg[x]) ))
    return all_reg


# TODO Change these path names to wherever the files for the batteries are stored
ini1 = '/home/pi/Documents/Codebase/MAX17330_MAX77958_MAX77818_REFDES/2000_mAh_EZ.INI'
# only run if program set to parallel charging mode
if parallel_charging is 1:
    ini2 = '/home/pi/Documents/Codebase/MAX17330_MAX77958_MAX77818_REFDES/2500_mAh_EZ.INI'


# Load up the .ini files for either a single charger or two chargers if parallel charging is turned on
fix_sid()
if(0x4b in search_max17330()):
    print("Start Loading Battery 1 Char File")
    chg1=MAX17330(sa=0x76)
    chg1.load_RAM_ini(ini1)
    print("Done Loading Battery 1 Char File")
# only run if program set to parallel charging mode
if parallel_charging is 1:
    # TODO FIX BUG: Uncomment either line depending on if the second MAX17330 (from the EVKIT) is found or not
    if(0x4f in search_max17330()): # default
    # if(0x0b in search_max17330()): # sometimes the evkit shows up as 0x0b depending on ALRT2 signal?
        print("Start Loading Battery 2 Char File")
        # TODO FIX BUG: Uncomment either line depending on if the second MAX17330 (from the EVKIT) is found or not
        chg2=MAX17330(0x72) # default
        # chg2=MAX17330(0x36) # sometimes the evkit shows up as 0x36 depending on ALRT2 signal?
        chg2.load_RAM_ini(ini2)
        print("Done Loading Battery 2 Char File")


# Log the data to a .csv file from the battery charging cycle from either one or two batteries
try:
    if chg1 is not None:
        _thread.start_new_thread(data_log,(chg1,"BC30_Dev1_{}.csv".format(time.strftime('%c') ),5))
    # only run if program set to parallel charging mode
    if parallel_charging is 1:
        if chg2 is not None:
            _thread.start_new_thread(data_log,(chg2,"BC30_Dev2_{}.csv".format(time.strftime('%c') ),5))
except:
    print("Unable to start thread")
try:
    _thread.start_new_thread(print_details,())
except:
    print("Unable to start print details thread")    


# unmask all ints
mask = [0b00000000, 0b00000000, 0b00000000, 0b00000000]
usb.write_reg(0x10,mask,4)
time.sleep(0.05)

# Read and clear all interrupts of the MAX77958
read_all_max77958_interrupts()
time.sleep(0.05)


#configure pdo variables
usb.configure_pdo_src_variables()
time.sleep(0.05)

# find capable pps devices
pps_pdo_ret = usb.find_pps_capable_pdo()
print("usb.find_pps_capable_pdo return value = ")
print(pps_pdo_ret)


# Read and clear all interrupts of the MAX77958
read_all_max77958_interrupts()
time.sleep(0.05)


# TODO make this automatic in a high level function later
# enable PPS mode
pps_ret = usb.set_pps(0x01, 0x2C, 0x01, 0x00) # Enable defualt voltage of 6 volts with no artificial current limit
print("usb.set_pps return value = {}".format(hex(pps_ret)))


# Read and clear all interrupts of the MAX77958
read_all_max77958_interrupts()
time.sleep(0.05)


# TODO make this automatic in a high level function later
# enable APDO if there is a PDO object that is PPS compatible with adjustable voltage
'''
if len(pps_pdo_ret) < 0:
    REQ_APDO_POS = pps_pdo_ret[0]
    print("REQ_APDO_POS value = {}".format(hex(REQ_APDO_POS)))
    apdo_ret = usb.set_APDO_SrcCap_Request(REQ_APDO_POS, usb.pps_voltage_min & 0x00FF, ((usb.pps_voltage_min & 0xff00) >> 8), OPERATING_CURRENT=0x00)
    print("usb.set_APDO_SrcCap_Request return value = {}".format(hex(apdo_ret)))
'''
# TODO you will need to see which of the APDO objects are PPS Compatible and put that down for this variable below, pay attention to the program start to see which of the APDOs support PPS charging. 
REQ_APDO_POS = 0x05
#apdo_ret = usb.set_APDO_SrcCap_Request(REQ_APDO_POS, (usb.conv_pdo_src_min_voltage[REQ_APDO_POS] & 0x00FF), ((usb.conv_pdo_src_max_voltage[REQ_APDO_POS] & 0xff00) >> 8), OPERATING_CURRENT=0x00)
apdo_ret = usb.set_APDO_SrcCap_Request(REQ_APDO_POS, 0xA5, 0x00, OPERATING_CURRENT=0x46) # Start off the voltage at 3.3 Volts and max current at 3500mA
#apdo_ret = usb.set_APDO_SrcCap_Request(REQ_APDO_POS, 0xFA, 0x00, OPERATING_CURRENT=0x28) # Start off the voltage at 5 Volts and max current at 2000mA
print("usb.set_APDO_SrcCap_Request return value = {}".format(hex(apdo_ret)))
print("current pdo selected",usb.curr_pdo_src_selected)
print() 
time.sleep(1.0)


# Read and clear all interrupts of the MAX77958
read_all_max77958_interrupts()
time.sleep(0.05)


# Run this to set the pps voltage to a good starting level to match either parallel or single battery charging mode 
initialize_good_pps_voltage()

# This enables the ICs to charge in parallel when program is set to parallel charging mode
if parallel_charging is 1:
    chg1.set_par_en_bit(1)
    chg2.set_par_en_bit(1)

# Main loop
while(1):
    # pps_sawtooth_test()
    # alt_qc_test()
    
    manage_charging_parallel()
    time.sleep(2)

    # print()
    # print("Memory contents of charger #1 ProtStatus register 0x0D9 {}".format(hex(chg1.rw(0x0D9,chg1.sa))))
    # print("Memory contents of charger #2 ProtStatus register 0x0D9 {}".format(hex(chg2.rw(0x0D9,chg2.sa))))
    # print()
    # print("Memory contents of charger #1 Status     register 0x000 {}".format(hex(chg1.rw(0x000,chg1.sa))))
    # print("Memory contents of charger #2 Status     register 0x000 {}".format(hex(chg2.rw(0x000,chg2.sa))))
    # print()
    # print("Memory contents of charger #1 Config2    register 0x0AB {}".format(hex(chg1.rw(0x0AB,chg1.sa))))
    # print("Memory contents of charger #2 Config2    register 0x0AB {}".format(hex(chg2.rw(0x0AB,chg2.sa))))
    # print()
    # print("Memory contents of charger #1 nPackCfg   register 0x1B5 {}".format(hex(chg1.rw(0x1B5,chg1.sa))))
    # print("Memory contents of charger #2 nPackCfg   register 0x1B5 {}".format(hex(chg2.rw(0x1B5,chg2.sa))))
    print()
