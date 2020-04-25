#!/usr/bin/python3
import argparse, subprocess, threading as t, tkinter as tk, tkinter.messagebox as tkmsg, re
from queue import Queue
from time import sleep
from os import system

def updateManuf():
    print('[+] Retrieving manufacturer database...')
    system('wget -q -N https://gitlab.com/wireshark/wireshark/raw/master/manuf')

def loadDb():

    try:
        with open('manuf', 'r') as file:
            db = file.readlines()

    except FileNotFoundError:
        print('[+] ERROR: Manufacturer database not found. Attempting to download now...')
        updateManuf()
        print('[+] Please try running again.')
        quit()

    for record in db:

        try:
            manufacturers[record.split('\t')[0]] = record.split('\t')[1].strip('\n')
        except IndexError:
            pass

def countManufacturers(manCount, addresses, interface):

    print(f'[+] Using interface {interface}')
    print('[+] Capturing preliminary data. Please wait...')

    p = subprocess.Popen(('sudo', 'tcpdump', '-i', interface, '-e', '-nn'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for row in iter(p.stdout.readline, b''):

        if stop:
            p.terminate()
            break

        if b'Beacon' not in row:
            try:
                mac1match = re.search('RA:.{2}:.{2}:.{2}:.{2}:.{2}:.{2}', row.rstrip().decode('utf-8'))

                if mac1match:
                    mac1match = mac1match.group(0).replace('RA:', '')

                mac2match = re.search('SA:.{2}:.{2}:.{2}:.{2}:.{2}:.{2}', row.rstrip().decode('utf-8'))

                if mac2match:
                    mac2match = mac2match.group(0).replace('SA:', '')

            except IndexError:
                continue
        else:
            
            beaconName = re.search('\(.*\)', row.rstrip().decode('utf-8')).group(0)[1:-1]
            BSSID = re.search('BSSID:.{2}:.{2}:.{2}:.{2}:.{2}:.{2}', row.rstrip().decode('utf-8')).group(0).replace('BSSID:', '')

            beaconPair = (beaconName, BSSID)

            if beaconName != '' and beaconName not in discoveredSSIDS:
                discoveredSSIDS.add(beaconName)
                bssidPairs.append(beaconPair)

                mOutput.put(f'New base station:\t{beaconName} - {BSSID}')
                messageData.append(f'BASE:{BSSID}|{beaconName}')

            elif beaconName in discoveredSSIDS:
                if beaconPair not in bssidPairs:
                    mOutput.put(f'Possible evil twin:\t{beaconName} - {BSSID}')
                    bssidPairs.append(beaconPair)

            continue

        for mac in [mac1match, mac2match]:
            if mac and mac not in discovered:
                discovered.add(mac)
                addresses.append(mac)
                oui = mac.upper()[:8]

                if oui in manufacturers:

                    if manufacturers[oui] not in manCount:
                        manCount[manufacturers[oui]] = 1
                        mOutput.put(f'New manufacturer:\t{manufacturers[oui]}')

                    else:
                        manCount[manufacturers[oui]] += 1

                    macOutput.put(f'{mac}\t{manufacturers[oui]}')

                else:
                    macOutput.put(mac)

def exportMacs():

    toWrite = addresses + messageData

    try:
        with open('recon_output.txt', 'w') as file:
            for a in toWrite:
                file.write('{}\n'.format(a))

        tkmsg.showinfo('Export', 'Exported to recon_output.txt')

    except:
        tkinter.messagebox.showinfo('Export', 'Export Failed')

def loadMacs():

    try:
        with open('recon_output.txt', 'r') as file:

            savedData = file.readlines()

        for line in savedData:

            if 'BASE:' not in line:

                if line.strip('\n') not in addresses:

                    addresses.append(line.strip('\n'))
                    discovered.add(line.strip('\n'))

                    oui = line.strip('\n').upper()[:8]

                    if oui in manufacturers:

                        if line in discovered:
                            pass

                        elif manufacturers[oui] not in manCount:
                            manCount[manufacturers[oui]] = 1
                    
                        else:
                            manCount[manufacturers[oui]] += 1

            elif 'BASE:' in line:

                beaconName = line.split('|')[1].strip('\n')
                BSSID = line.split('|')[1].replace('BASE:', '').strip('\n')

                beaconPair = (beaconName, BSSID)

                if beaconName != '' and beaconName not in discoveredSSIDS:
                    discoveredSSIDS.add(beaconName)
                    bssidPairs.append(beaconPair)
                    messageData.append(f'BASE:{BSSID}|{beaconName}')

                elif beaconName in discoveredSSIDS:
                    if beaconPair not in bssidPairs:
                        bssidPairs.append(beaconPair)

        tkmsg.showinfo('Load', 'Data loaded successfully')

    except FileNotFoundError:
        tkmsg.showinfo('Load', 'File not found')
    
    except Exception as e:
     tkmsg.showinfo('Load', 'Error whilst loading data:\n' + str(e))

def refresher():

    global bars

    if len(bars) != 0:
        for b in bars:
            c.delete(b)
        bars = []

    manCountSorted = sorted(manCount.items(), key=lambda x: x[1], reverse=True)
    norms = [float(count[1])/manCountSorted[0][1] for count in manCountSorted]

    y_stretch = 250
    y_gap = 20
    x_stretch = 20
    x_width = 80
    x_gap = 20
    c_width = 1050
    c_height = 600/2

    for x, y in enumerate(manCountSorted):
        
        if x > 9:
            break

        x0 = x * x_stretch + x * x_width + x_gap
        y0 = c_height - norms[x] * y_stretch
        x1 = x * x_stretch + x * x_width + x_width + x_gap
        y1 = c_height - y_gap

        bar = c.create_rectangle(x0, y0, x1, y1, fill='chartreuse2')
        barText = c.create_text(x0+2, y0, anchor=tk.SW, text='{}: {}'.format(str(y[0]), y[1]), fill='white')
            
        bars.append(bar)
        bars.append(barText)

    root.after(5000, refresher)

def displayOutput():

    macList = ''

    while True:
        while not macOutput.empty() and not stop:
            macDetails = macOutput.get(block=False)

            if macDetails is None:
                break

            macList += macDetails + '\n'
            outputText.set(macList)
            macOutput.task_done()

        if stop:
            break

def messageOutput():

    messageList = ''

    while True:
        while not mOutput.empty() and not stop:
            message = mOutput.get(block=False)

            if message is None:
                break

            messageList += message + '\n'
            messageText.set(messageList)
            mOutput.task_done()

        if stop:
            break

def runGui():

    while len(manCount) == 0:
        sleep(2)
        if len(manCount) == 0:
            print('[+] No device information captured yet...')
    
    global root
    root = tk.Tk()
    root.title("Recon")
    root.resizable(0, 0) 
    c_width = 1050
    c_height = 600

    topFrame = tk.Frame(root, width=c_width, height=300, bg='grey8')
    topFrame.pack(side=tk.TOP, fill=tk.BOTH)

    outputFrame = tk.Frame(topFrame, width=c_width/2, height=300, bg='grey8')
    outputFrame.pack_propagate(0)
    outputFrame.pack(side=tk.LEFT, fill=tk.BOTH)
    
    global outputText
    outputText = tk.StringVar()
    outputText.set('Incoming MACS...')
    outputTextWindow = tk.Message(outputFrame, textvariable=outputText, justify=tk.LEFT, width=c_width/2, anchor=tk.SW, fg='white', bg='grey8')
    outputTextWindow.pack(fill=tk.BOTH)

    messageFrame = tk.Frame(topFrame, width=c_width/2, height=300, bg='grey8')
    messageFrame.pack_propagate(0)
    messageFrame.pack(fill=tk.BOTH)

    global messageText
    messageText = tk.StringVar()
    messageText.set('Incoming messages...')
    messageTextWindow = tk.Message(messageFrame, textvariable=messageText, justify=tk.LEFT, width=c_width/2, anchor=tk.SW, fg='white', bg='grey8')
    messageTextWindow.pack(fill=tk.BOTH)

    global c
    c = tk.Canvas(root, width=c_width, height=c_height/2, bg='grey8')
    c.pack()

    btnExport = tk.Button(root, text='Export', command=exportMacs)
    btnExport.pack(side=tk.LEFT)

    btnLoad = tk.Button(root, text='Load', command=loadMacs)
    btnLoad.pack(side=tk.LEFT)

    btnExit = tk.Button(root, text='Exit', command=root.destroy)
    btnExit.pack(side=tk.RIGHT)

    global bars
    bars = []

    t.Thread(target=displayOutput).start()
    t.Thread(target=messageOutput).start()
    t.Thread(target=refresher).start()

    root.mainloop()

argparser = argparse.ArgumentParser(description='Blockade-Recon 0.1')
argparser.add_argument('-i', '--interface', default='wlan0mon', help='Specify a wireless interface to listen on')
argparser.add_argument('-u', '--updatedb', action='store_true', help='Attempt to retrieve an updated version of the manufacturer database')
args = argparser.parse_args()
    
manCount = dict()
addresses = list()
manufacturers = dict()
discovered = set()
messageData = list()
discoveredSSIDS = set()
bssidPairs = list()

print('Recon 0.1')

loadDb()

interface = args.interface
updatedb = args.updatedb

if updatedb:
    updateManuf()

macOutput = Queue()
mOutput = Queue()

monitoringThread = t.Thread(target=countManufacturers, args=(manCount,addresses,interface,))
monitoringThread.start()

stop = False
runGui()
stop = True
monitoringThread.join()
print('[+] Goodbye!')
