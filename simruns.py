from madNUN import *
import numpy as np
import matplotlib.pyplot as plt
import cv2 as cv

f_check_r = 3   # final check range - in each direction

def update_m_map(b_s, c_s):
    m_map = np.zeros((512, 512, 3), 'uint8')
    t = time.perf_counter()
    for key in database.keys():
        if (key[2], key[3]) == (b_s, c_s):
            m_map[key[0]//8, key[1]//8, :] += 31
    cv.imshow('map', m_map)
    cv.waitKey(1)
    print("map updated in", round(time.perf_counter() - t,1), "s")

def get_simulation():
    sim = simulate()
    sim['beta'] = sim['ic_dut']/sim['ib_dut']
    return sim

def tune_by(tune, by, target, inf):
    assert inf in ("direct", "inverse") , "inf is " + str(inf) + \
           " but should be 'direct' or 'inverse'"
    assert by in ("dac0", "dac1"), "tune is " + str(tune) + \
           " but should be 'dac0' or 'dacc1'"
    
    state = get_simulation()
    set_dac = set_dac0_bin if (by == "dac0") else set_dac1_bin
    dac_state = lambda : dac0_bin() if (by == "dac0") else dac1_bin()
    jump = 1
    inf = 1 if (inf == "direct") else -1
    direction = 1 if (target - state[tune])*inf > 0 else -1

    while True:
        print("dac state:", dac_state(), " | jump:", jump, \
              " | state:", state[tune])
        if dac_state() + jump*direction < 0:
            set_dac(0); print("out of range")
        elif dac_state() + jump*direction > 4095:
            set_dac(4095); print("out of range")
        else:
            set_dac( dac_state() + jump*direction )
        state = get_simulation()
        if (target - state[tune])*inf*direction < 0:
            break
        if dac_state() == 4095 and direction > 0:
            print("dac maximum exceeded")
            return 'top_breach'
        if dac_state() == 0 and direction < 0:
            print("dac minimum exceeded")
            return 'bottom_breach'
        jump *= 2
        
    print("\t\tzooming in")
    while jump > 1:
        jump //= 2
        state = get_simulation()
        direction = 1 if (target - state[tune])*inf > 0 else -1
        set_dac( dac_state() + jump*direction )
        print("dac state:", dac_state(), " | jump:", jump, \
              " | state:", state[tune])

    print("\t\tfinal check")
    dis = {}
    for i in range(dac_state() - f_check_r, dac_state() + f_check_r):
        set_dac(i)
        state = get_simulation()
        dis[i] = abs(state[tune] - target)
        print("dac state:", dac_state(), " | abs error:", abs(state[tune] - target), \
              "| rel error", round((100*abs(state[tune] - target)/target),1), "% | state:", state[tune])
        
    ideal_dac = list(dis.keys())[list(dis.values()).index(min(list(dis.values())))]
    set_dac(ideal_dac)
    print("ideal dac:", ideal_dac)
    return ideal_dac

def ic_vce(ibs):
    data = {}
    for ib in ibs:
        ib_data = []
        for vtop in list(range(0,1000,50)) + list(range(1000,4055,200)):
            #update_m_map(b_s=1, c_s=2)
            set_dac0_bin(vtop)
            tune_by("ib_dut","dac1", ib, "direct")
            ib_data.append(simulate())
        data[ib] = ib_data
    return data

def hfe_ic(vce):
    data = []
    for vb in range(0,1200, 10):
        print("\n\n\t\t", vb, "\n\n")
        set_dac1_bin(vb)
        tune_by('vc', 'dac0', vce, 'direct')
        data.append(simulate())
    return data

def sat_ic(beta):
    data = []
    set_base_switches("1k")
    for vb in range(450,4060, 50):
        print("\n\n\t\t", vb, "\n\n")
        set_dac1_bin(vb)
        tune_by('beta', 'dac0', beta, 'direct')
        data.append(get_simulation())
        print("DATA: \tIb", data[-1]['ib_dut'],"\tIc", data[-1]['ic_dut'])

    print("switching to base resistor 100")
    set_base_switches("100")
    tune_by('ic_dut','dac1',data[-1]['ic_dut']*0.9,'direct')

    for vb in range((dac1_bin()//50)*50,4060, 50):
        print("\n\n\t\t", vb, "\n\n")
        set_dac1_bin(vb)
        tune_by('beta', 'dac0', beta, 'direct')
        data.append(get_simulation())
        print("DATA: \tIb", data[-1]['ib_dut'],"\tIc", data[-1]['ic_dut'])
   
    return data

def plot_graphs():
    fig, plots = plt.subplots(2,2)

    res = ic_vce([1e-04,2e-04,3e-04,4e-04,5e-04,6e-04,7e-04,8e-04,9e-04,0.001])
    for i in res.keys():
        plots[0,0].plot([k['vc'] for k in res[i]], [k['ic_dut'] for k in res[i]], label = str(i))
    plots[0,0].legend()
    plots[0,0].set_title("Ic - Vce"); plots[0,0].set_xlabel('Vce'); plots[0,0].set_ylabel('Ic');

    fig.show()
    set_dac0_bin(0)
    res = hfe_ic(4)
    res = [k for k in res if ( (k['ic_dut'] < 0.6) and (k['ic_dut'] > 0.0001) )]
    plots[0,1].plot([k['ic_dut'] for k in res], [k['ic_dut']/k['ib_dut'] for k in res])
    plots[0,1].set_xscale('log')
    plots[0,1].set_title("hfe - Ic"); plots[0,1].set_xlabel('Ic'); plots[0,1].set_ylabel('hfe');

    fig.show()
    res = sat_ic(10)
    res = [p for p in res if (p['ic_dut'] > 0.001)]
    plots[1,0].plot([k['ic_dut'] for k in res], [k['vc'] for k in res])
    plots[1,0].set_title("CEsat - ic")
    plots[1,0].set_xscale('log'); plots[1,0].set_xlabel('Ic'); plots[1,0].set_ylabel('Vce');

    plots[1,1].plot([k['ic_dut'] for k in res], [k['vb'] for k in res])
    plots[1,1].set_title("BEsat - ic")
    plots[1,1].set_xscale('log'); plots[1,1].set_xlabel('Ic'); plots[1,1].set_ylabel('Vbe');

    fig.show()
    return fig, plots
    
print(dac0_bin(), dac1_bin())
'''
res = ic_vce([1e-04,2e-04,3e-04,4e-04,5e-04,6e-04,7e-04,8e-04,9e-04,0.001])
for i in res.keys():
    plt.plot([k['vc'] for k in res[i]], [k['ic_dut'] for k in res[i]], label = str(i))
plt.legend()
plt.show()

res = hfe_ic(4)
res = [k for k in res if ( (k['ic_dut'] < 0.6) and (k['ic_dut'] > 0.0001) )]
plt.plot([k['ic_dut'] for k in res], [k['ic_dut']/k['ib_dut'] for k in res])
plt.xscale('log')
plt.show()

res = sat_ic(10)
res = [p for p in res if (p['ic_dut'] > 0.0001)]
plt.plot([k['ic_dut'] for k in res], [k['vc'] for k in res])
plt.title("CEsat - ic")
plt.xscale('log')
plt.show()

#fig, plots = plot_graphs()

data0 = []; data1 = []

for vb in range(500,50,4060):
    set_base_switches('1k')
    tune_by('beta','dac0', 10, 'direct')
    data0.append(simulate())
    set_base_switches('100')
    tune_by('beta','dac0', 10, 'direct')
    data1.append(simulate())'''
'''
res = sat_ic(10)
res = [r for r in res if r['ic_dut'] > 0.001]
plt.plot([i['ic_dut'] for i in res],[i['vc'] for i in res])
plt.xscale('log')
plt.show()

data = []
set_collector_switches("10")
set_base_switches("100")

for vb in range(450,1000, 50):
    print("\n\n\t\t", vb, "\n\n")
    set_dac1_bin(vb)
    tune_by('beta', 'dac0', 10, 'direct')
    data.append(get_simulation())
    data[-1]['dac0_bin'] = dac0_bin(); data[-1]['dac1_bin'] = dac1_bin();
    print("DATA: \tIb", data[-1]['ib_dut'],"\tIc", data[-1]['ic_dut'])
    
res = [p for p in data if (p['ic_dut'] > 0.001)]
plt.plot([k['ic_dut'] for k in res], [k['vc'] for k in res])
plt.title("CEsat - ic")
plt.xscale('log')
plt.show()
'''

set_collector_switches('10')
set_dac0_bin(2000)

ers = []
r = [0.0001, 0.0002, 0.00030000000000000003, 0.0004, 0.0005, 0.0006000000000000001, 0.0007, 0.0008, 0.0009000000000000001]

for i in r:
    ers.append([])
    set_base_switches('1k')
    tune_by('ib_dut', 'dac1', i, 'direct')
    err = abs(simulate()['ib_dut'] - i)
    ers[-1].append(err)
    
    set_base_switches('100')
    tune_by('ib_dut', 'dac1', i, 'direct')
    err = abs(simulate()['ib_dut'] - i)
    ers[-1].append(err)
