#%%
import smbus,time,os,_thread
from MAX17330 import MAX17330
import RPi.GPIO as GPIO
bus=smbus.SMBus(1)

GPIO.setmode(GPIO.BOARD)
Alrt1=13
Alrt2=15
GPIO.setup(Alrt1,GPIO.OUT)
GPIO.setup(Alrt2,GPIO.OUT)


def change_SID(sid, gotosid=0):
    #GPIO must be managed externally.
    bus.write_word_data(sid,0x61,0)
    bus.write_word_data(sid,0x61,0)
    bus.write_word_data(0x0b,0x2b,(gotosid<<4)|1)
    new_sa={0:0x76,1:0x32,2:0x72,3:0x36}[gotosid]
    tstart=time.time()
    while (time.time() - tstart) <2:
        try:
            bus.write_quick(new_sa)
            #print("Found device at address {}".format(hex(new_sa)))
            return 1
        except:
            time.sleep(0.05)
    if (time.time() - tstart) >=2:
        print("Changing Slave ID timed out")
        return 1
    prev_val = bus.read_word_data(new_sa,0x61)
    val = (prev_val & 0xFF07) | 0xF8
    bus.write_word_data(new_sa,0x61,val)

def search_MAX17330():
    found_devs=[]
    for addr in [0x4b,0x0f,0x4f,0x0b]:
        try:
            bus.write_quick(addr)
            found_devs.append(addr)
        except:
            pass
    return found_devs

def fix_sid():
    devs=search_MAX17330()
    if len(devs)<1:
        print("No MAX17330 Secondary slave addresses found.  Exiting fix_sid routine")
        return 0
    if 0x4B in devs:
        print("MAX17330 Device 1 is already at correct slave address")
    elif 0x0b in devs:
        GPIO.output(Alrt1,GPIO.HIGH)
        GPIO.output(Alrt2,GPIO.LOW)
        change_SID(0x36,0)
        if(search_MAX17330() == devs):
            print("No change after trying to move Device 1.  Check power to Device 1")
        else:
            print("MAX17330 Device 1 moved to SID 0x76, 0x4B")
    devs=search_MAX17330()
    if 0x4F in devs:
        print("MAX17330 Device 2 is already at correct slave address")
    elif 0x0b in devs:
        GPIO.output(Alrt1,GPIO.LOW)
        GPIO.output(Alrt2,GPIO.HIGH)
        change_SID(0x36,2)
        if(search_MAX17330() == devs):
            print("No change after trying to move Device 2.  Check power to Device 2")
        else:
            print("MAX17330 Device 2 moved to SID 0x72, 0x4F")

def reset_to_NVM_SID():
    for addr in [0x72,0x32,0x76]:
        try:
            bus.write_word_data(addr,0x60,0x000F)
        except:
            pass

def _read_log_line(dev,max_tries=10):
    from datetime import datetime
    data=dev.read_line()
    timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    return timestamp + ',' + ','.join(map(hex,data))

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


fix_sid()
if(0x4b in search_MAX17330()):
    chg1=MAX17330(sa=0x76)
if(0x4f in search_MAX17330()):
    chg2=MAX17330(sa=0x72)
GPIO.cleanup()

def print_details():
    import time,sys
    while True:
        time.sleep(1)
        try:
            if chg1 is not None:
                try:
                    print("Device 1:    VCell = {}   IChg = {}   Target = {}    VSYS={} ".format(chg1.get_vcell(),chg1.get_ibatt(),chg1.get_ichg(),chg1.get_vpckp()))
                except:
                    print("Error reading CHG1")
            else:
                print("No CHG1")
            # if chg2 is not None:
            #     try:
            #         print("Device 2:    VCell = {}   IChg = {}   Target = {}    VSYS={} ".format(chg2.get_vcell(),chg2.get_ibatt(),chg2.get_ichg(),chg2.get_vpckp()))
            #     except:
            #         print("Error reading CHG2")
        except KeyboardInterrupt:
            print("User stopped logging.")
            return

try:
    if chg1 is not None:
        _thread.start_new_thread(data_log,(chg1,"BC30_Dev1_{}.csv".format(time.strftime('%c') ),5))
    # if chg2 is not None:
    #     _thread.start_new_thread(data_log,(chg2,"BC30_Dev2_{}.csv".format(time.strftime('%c') ),5))
except:
    print("Unable to start thread")
try:
    _thread.start_new_thread(print_details,())
except:
    print("Unable to start print details thread")    



while(1):
    time.sleep(1)