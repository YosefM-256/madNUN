from madNUN import *
import matplotlib.pyplot as plt
import numpy as np

final_check_range = 5       # in each direction

def tune_dac1(target_ib):
    global dac1; dac1_value = dac1_bin();
    print(dac1_value)
    data = []
    print(simulate())
    current_ib = simulate()['ib_dut']
    jump = 2
    direction = (1 if (target_ib - current_ib) > 0 else -1)
    
    while (target_ib - current_ib)*direction > 0:
        if dac1_value > 4095:
            print("maximum exceeded")
        direction = (1 if (target_ib - current_ib) > 0 else -1)
        print(simulate()['ib_dut'], target_ib, dac1_value, jump, direction, dac1_bin())
        set_dac1_bin(dac1_value + jump*direction)
        dac1_value += jump*direction
        jump *= 2
        current_ib = simulate()['ib_dut']
        data.append(simulate())

    direction = (1 if (target_ib - current_ib) > 0 else -1)
    while jump > 1:
        print(simulate()['ib_dut'], target_ib, dac1_value, jump, direction, dac1_bin())
        jump //= 2
        current_ib = simulate()['ib_dut']
        data.append(simulate())
        direction = (1 if (target_ib - current_ib) > 0 else -1)
        set_dac1_bin(dac1_value + jump*direction)
        dac1_value += jump*direction

    final_check_data = {}
    for i in range(dac1_value - final_check_range, dac1_value + final_check_range, 1):
        dac1_value = i
        set_dac1_bin(dac1_value)
        final_check_data[i] = abs(simulate()['ib_dut'] - target_ib)
        
    ideal_dac1 = list(final_check_data.keys())[list(final_check_data.values()).index(min(list(final_check_data.values())))]
    set_dac1_bin(ideal_dac1)
    data.append(simulate())
    print("final check:\n", final_check_data)
    return data
        
def vce_ic(target_ib):
    data = []
    for vtop in list(range(0,1024, 8)) + list(range(1024,4096,64)):
        print("####\t", vtop, "\t####")
        set_dac0_bin(vtop)
        tune_dac1(target_ib)
        data.append(simulate())
    return data  

def ic_hfe(mini, maxi, ticks):
    for ic in range(np.log10(mini), np.log10(maxi), ticks):
        tune_dac1_per_ic(ic)
        point = simulate()

set_base_switches('100')
set_collector_switches('10')
set_dac0_bin(4095)
set_dac1_bin(4095)

data = vce_ic(0.0001)
ic = [i['ic_dut'] for i in data]
vce = [i['vc'] for i in data]
plt.plot(vce,ic)
plt.show()
#data = tune_dac1(0.001)
