import subprocess, threading as t, tkinter as tk, tkinter.messagebox as tkmsg
from time import sleep

def countManufacturers(manCount, addresses):

    with open('manuf', 'r') as file:
        db = file.readlines()

    manufacturers = dict()

    global discovered
    discovered = set()

    for record in db:
        manufacturers[record.split('\t')[0]] = record.split('\t')[1].strip('\n')

    p = subprocess.Popen(('sudo', 'tcpdump', '-i', 'wlan0mon', '-e', '-nn'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
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

    global addresses

    try:
        with open('recon_output.txt', 'w') as file:
            for a in addresses:
                file.write('{}\n'.format(a))

        tkmsg.showinfo('Export', 'Exported to recon_output.txt')

    except:
        tkinter.messagebox.showinfo('Export', 'Export Failed')

def loadMacs():

    global addresses
    global discovered

    try:
        with open('recon_output.txt', 'r') as file:
            macs = file.readlines()

        for mac in macs:
            
            if mac not in addresses:
                addresses.append(mac.strip('\n'))
            
            discovered.add(mac.strip('\n'))

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

    y_stretch = 30
    y_gap = 20
    x_stretch = 20
    x_width = 80
    x_gap = 20
    c_width = 1050
    c_height = 600

    for x, y in enumerate(sorted(manCount.items(), key=lambda x: x[1], reverse=True)):
        
        if x > 9:
            break

        x0 = x * x_stretch + x * x_width + x_gap
        y0 = c_height - (y[1] * y_stretch + y_gap)
        x1 = x * x_stretch + x * x_width + x_width + x_gap
        y1 = c_height - y_gap

        bar = c.create_rectangle(x0, y0, x1, y1, fill="red")
        barText = c.create_text(x0+2, y0, anchor=tk.SW, text='{}: {}'.format(str(y[0]), y[1]))
            
        bars.append(bar)
        bars.append(barText)

    root.after(5000, refresher)

def runGui():
    print('Recon 0.1')
    print('[+] Capturing preliminary data. Please wait...')

    while len(manCount) == 0:
        sleep(10)
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
    
manCount = dict()
addresses = list()

monitoringThread = t.Thread(target=countManufacturers, args=(manCount,addresses,))
monitoringThread.start()

stop = False
runGui()
stop = True
monitoringThread.join()
print('[+] Goodbye!')
