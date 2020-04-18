#!/usr/bin/python3
import argparse, subprocess, threading as t, tkinter as tk, tkinter.messagebox as tkmsg
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

    print('[+] Using interface {}'.format(interface))
    print('[+] Capturing preliminary data. Please wait...')

    p = subprocess.Popen(('sudo', 'tcpdump', '-i', interface, '-e', '-nn'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    for row in iter(p.stdout.readline, b''):

        if stop:
            p.terminate()
            break

        try:
            mac = row.rstrip().decode('utf-8').split()[15][3:]
        except IndexError:
            pass

        if mac not in discovered and ':' in mac and mac != 'ff:ff:ff:ff:ff:ff' and 'ID' not in mac:
            discovered.add(mac)
            addresses.append(mac)
            oui = mac.upper()[:8]

            if oui in manufacturers:

                if manufacturers[oui] not in manCount:
                    manCount[manufacturers[oui]] = 1

                else:
                    manCount[manufacturers[oui]] += 1

def exportMacs():

    try:
        with open('recon_output.txt', 'w') as file:
            for a in addresses:
                file.write('{}\n'.format(a))

        tkmsg.showinfo('Export', 'Exported to recon_output.txt')

    except:
        tkinter.messagebox.showinfo('Export', 'Export Failed')

def loadMacs():

    try:
        with open('recon_output.txt', 'r') as file:
            macs = file.readlines()

        for mac in macs:
            
            if mac not in addresses:
                addresses.append(mac.strip('\n'))
            
                discovered.add(mac.strip('\n'))

                oui = mac.upper()[:8]

                if oui in manufacturers:

                    if mac in discovered:
                        pass

                    elif manufacturers[oui] not in manCount:
                        manCount[manufacturers[oui]] = 1
                
                    else:
                        manCount[manufacturers[oui]] += 1

        tkmsg.showinfo('Load', 'Data loaded successfully')

    except FileNotFoundError:
        tkmsg.showinfo('Load', 'File not found')
    
    except:
     tkmsg.showinfo('Load', 'Error whilst loading data')

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
    c_height = 600

    for x, y in enumerate(manCountSorted):
        
        if x > 9:
            break

        x0 = x * x_stretch + x * x_width + x_gap
        y0 = c_height - norms[x] * y_stretch
        x1 = x * x_stretch + x * x_width + x_width + x_gap
        y1 = c_height - y_gap

        bar = c.create_rectangle(x0, y0, x1, y1, fill="red")
        barText = c.create_text(x0+2, y0, anchor=tk.SW, text='{}: {}'.format(str(y[0]), y[1]))
            
        bars.append(bar)
        bars.append(barText)

    root.after(5000, refresher)

def runGui():

    while len(manCount) == 0:
        sleep(2)
        if len(manCount) == 0:
            print('[+] No device information captured yet...')
    
    global root
    root = tk.Tk()
    root.title("Recon")
    c_width = 1050
    c_height = 600

    global c
    c = tk.Canvas(root, width=c_width, height=c_height, bg='grey90')
    c.pack()

    btnExport = tk.Button(root, text='Export', command=exportMacs)
    btnExport.pack(side=tk.LEFT)

    btnLoad = tk.Button(root, text='Load', command=loadMacs)
    btnLoad.pack(side=tk.LEFT)

    btnExit = tk.Button(root, text='Exit', command=root.destroy)
    btnExit.pack(side=tk.RIGHT)

    global bars
    bars = []

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

print('Recon 0.1')

loadDb()

interface = args.interface
updatedb = args.updatedb

if updatedb:
    updateManuf()

monitoringThread = t.Thread(target=countManufacturers, args=(manCount,addresses,interface,))
monitoringThread.start()

stop = False
runGui()
stop = True
monitoringThread.join()
print('[+] Goodbye!')
