import os
import time

''' as a rule, in this program, the higher order index of a switch controlling voltage source
controlles the lower resistance
'''

blueprint_file = "circuit_blueprint1 - 2n2222.cir"
new_file = "simulation.cir"
user_var_file = "net_to_user_names.txt"
dataset_file = "dataset - 2N2222.txt"
switch_check = True
forward_sim = True
forward_sim_range = 20 # in each direction
global database; database = {}
global collector_switches; collector_switches = [0,0,5]
global base_switches; base_switches = [0,5]
global dac0; dac0 = 0
global dac1; dac1 = 0

class Measurement:
    def __init__(self, spice_name = None, user_name = None, value = None):
        self.user_name = user_name
        self.spice_name = spice_name
        self.value = value

    def __repr__(self):
        return self.user_name + " :\t" + str(self.value)
    
def read_blueprint():
    file = open(blueprint_file, 'r')
    blueprint = file.readlines()
    file.close()
    return blueprint

def create_simulation(jump = 1, sweep = 'none'):
    if not( sweep in ['none', 'dac0', 'dac1'] ):
        raise TypeError(str(sweep) + "is not a valid argument")
    blueprint = read_blueprint()
    set_voltages(blueprint)
    if sweep == 'none':
        blueprint[-3] = ".op\n"
    elif sweep == 'dac0':
        set_dc_sweep(blueprint, jump = jump, sweep ='dac0')
    elif sweep == 'dac1':
        set_dc_sweep(blueprint, jump = jump, sweep ='dac1')
    save_simulation(blueprint)
    
def set_voltages(blueprint):
    new_circuit = ""

    # set dac0 (collector)
    global dac0 
    dac0_index = blueprint.index("*## Multisim Component V6 ##*\n")
    blueprint[dac0_index + 1] = "vV6 6 0 dc " + str(dac0) + " ac 0 0\n"     

    # set dac1 (base)
    global dac1
    dac1_index = blueprint.index("*## Multisim Component V1 ##*\n")
    blueprint[dac1_index + 1] = "vV1 2 0 dc " + str(dac1) + " ac 0 0\n"

    check_switches()
    global collector_switches
    # set switch_c_2 (Rc3 = 10 ohm)
    switch_c_2_index = blueprint.index("*## Multisim Component V8 ##*\n")
    blueprint[switch_c_2_index + 1] = "vV8 SC1_l_Vin_dig 0 dc " + str(collector_switches[2]) + " ac 0 0\n"     

    # set switch_c_1 (Rc2 = 100 ohm)
    switch_c_1_index = blueprint.index("*## Multisim Component V4 ##*\n")
    blueprint[switch_c_1_index + 1] = "vV4 SC2_l_Vin_dig 0 dc " + str(collector_switches[1]) + " ac 0 0\n"     

    # set switch_c_0 (Rc1 = 1k ohm)
    switch_c_0_index = blueprint.index("*## Multisim Component V2 ##*\n")
    blueprint[switch_c_0_index + 1] = "vV2 SC3_l_Vin_dig 0 dc " + str(collector_switches[0]) + " ac 0 0\n"     

    global base_switches
    # set switch_b_1 (Rb2 = 100 ohm)
    switch_b_1_index = blueprint.index("*## Multisim Component V3 ##*\n")
    blueprint[switch_b_1_index + 1] = "vV3 1 0 dc " + str(base_switches[1]) + " ac 0 0\n"     

    # set switch_b_0 (Rb1 = 1k ohm)
    switch_b_0_index = blueprint.index("*## Multisim Component V7 ##*\n")
    blueprint[switch_b_0_index + 1] = "vV7 15 0 dc " + str(base_switches[0]) + " ac 0 0\n"     

def set_dc_sweep(blueprint, sweep, jump = 1):
    global dac0; global dac1;
    voltage_jumps = 5.0*jump/4096
    edges = dc_sweep_range(jump)
    
    dac0_range = {'up': min(4095, edges["dac0_high_bin"])*5/4096, \
                  'down': max(0, edges["dac0_low_bin"])*5/4096 }
    dac1_range = {'up': min(4095, edges["dac1_high_bin"])*5/4096, \
                  'down': max(0, edges["dac1_low_bin"])*5/4096 }
    if sweep == 'dac0':       
        blueprint[-3] = ".dc vv6 " + str(round(dac0_range['down'], 6)) + ' ' + str(round(dac0_range['up'], 6)) \
                    + ' ' + str(round(voltage_jumps, 6)) + '\n'
        print("simulating dac0", (max(0, edges["dac0_low_bin"]), min(4095, edges["dac0_high_bin"])))
    if sweep == 'dac1':
        blueprint[-3] = ".dc vv1 " + str(round(dac1_range['down'], 6)) + ' ' + str(round(dac1_range['up'], 6)) \
                    + ' ' + str(round(voltage_jumps, 6)) + '\n'
        print("simulating dac1", (max(0, edges["dac1_low_bin"]), min(4095, edges["dac1_high_bin"])))
    return dac0_range, dac1_range

def dc_sweep_range(jump):
    global database
    global collector_switches; global base_switches;
    global dac0; global dac1;
    dac0_bin = int(round(dac0*4096/5, 0))
    dac1_bin = int(round(dac1*4096/5, 0))
    c_switch = collector_switches.index(5)
    b_switch = base_switches.index(5)
    
    dac0_low_bin = dac0_bin
    dac0_high_bin = dac0_bin
    dac1_low_bin = dac1_bin
    dac1_high_bin = dac1_bin
    
    for i in range(dac0_bin - jump*forward_sim_range, dac0_bin, jump):
        if not( (i, dac1_bin, b_switch, c_switch) in database.keys() ):
            dac0_low_bin = i
            break
    for i in range(dac0_bin + jump*forward_sim_range, dac0_bin, -1*jump):
        if not( (i, dac1_bin, b_switch, c_switch) in database.keys() ):
            dac0_high_bin = i
            break
    for i in range(dac1_bin - jump*forward_sim_range, dac1_bin, jump):
        if not( (dac0_bin, i, b_switch, c_switch) in database.keys() ):
            dac1_low_bin = i
            break
    for i in range(dac1_bin + jump*forward_sim_range, dac1_bin, -1*jump):
        if not( (dac0_bin, i, b_switch, c_switch) in database.keys() ):
            dac1_high_bin = i
            break      
    return {"dac0_low_bin": dac0_low_bin, "dac0_high_bin": dac0_high_bin, \
            "dac1_low_bin": dac1_low_bin, "dac1_high_bin": dac1_high_bin}

def save_simulation(blueprint):
    file = open(new_file, 'w')
    file.writelines(blueprint)
    file.close()

def run_simulation():
    # runs the simulation
    os.chdir("C:\\Program Files\\LTC\\LTspiceXVII") # changes directory
    command = "XVIIx64.exe -b -ascii C:\\Users\\mizra\\Desktop\\madNUN\\" + new_file
    #command = "XVIIx64.exe -b C:\\Users\\mizra\\Desktop\\madNUN\\" + new_file
    t = time.perf_counter()
    print("started simulation")
    os.system(command)
    print("simulataed for", round(time.perf_counter() - t, 1), "seconds")
    time.sleep(2)
    os.chdir("C:\\Users\\mizra\\Desktop\\madNUN") # changes back directory

def read_user_variables():
    user_variables_file = open(user_var_file, 'r')
    measurements = []
    for line in user_variables_file.readlines():
        measurements.append(Measurement(spice_name = line.split('\t')[0], user_name = line.split('\t')[1].strip('\n')))
    user_variables_file.close()
    return measurements

def read_sim_data(measurements):
    data_file = open(new_file[:-4] + '.raw', 'r')
    simulation_data = data_file.read(200000).strip('\n')
    data_file.close()
    s_simulation_data = simulation_data.split('\n')
    s_simulation_vars = s_simulation_data[s_simulation_data.index("Variables:")+1 : \
                                          s_simulation_data.index("Values:")]
    s_simulation_values = s_simulation_data[ s_simulation_data.index("Values:")+1 : ]
    s_simulation_vars = [data.strip('\t').split('\t')[1] for data in s_simulation_vars]
    s_simulation_values[0] = s_simulation_values[0][1:]
    s_simulation_values = [float(data.strip('\t')) for data in s_simulation_values]
    for measurement in measurements:
        measurement.value = s_simulation_values[s_simulation_vars.index(measurement.spice_name)]
    sim_run = {}
    for measurement in measurements:
        sim_run[measurement.user_name] = measurement.value
    return sim_run

def read_sim_results(measurements):
    data_file = open(new_file[:-4] + '.raw', 'r')
    simulation_data = data_file.read().strip('\n')
    data_file.close()
    s_simulation_data = simulation_data.split('\n')
    s_simulation_vars = s_simulation_data[s_simulation_data.index("Variables:")+1 : \
                                          s_simulation_data.index("Values:")]
    s_simulation_vars = [data.strip('\t').split('\t')[1] for data in s_simulation_vars]
    s_simulation_values = simulation_data.split("\t\t")[1:]
    for j in range(len(s_simulation_values)):
        s_simulation_values[j] = s_simulation_values[j].split("\n\t")
        s_simulation_values[j][-1] = s_simulation_values[j][-1].split('\n')[0]
        #debug start
        f = open('debug.txt', 'w')
        f.writelines([k+'\n' for k in s_simulation_values[j]])
        f.close()
        #debug end
        s_simulation_values[j] = [float(point) for point in s_simulation_values[j]]

    sim_results = []
    for op_point in s_simulation_values:
        op_point_dict = {}
        for measurement in measurements:
            op_point_dict[measurement.user_name] = op_point[s_simulation_vars.index(measurement.spice_name)]
        sim_results.append(op_point_dict)
    return sim_results

def set_base_switches(switch):
    ''' choose between 0 or "1k" and 1 or "100"'''
    global base_switches;
    if switch in ('1k',0):
        base_switches = [5,0]
        return
    if switch in ('100',1):
        base_switches = [0,5]
        return
    raise ValueError(str(switch) + " is an invalid argument")

def set_collector_switches(switch):
    ''' choose between 0 or "1k", 1 or "100" and 2 or "10"'''
    global collector_switches;
    if switch in ('1k',0):
        collector_switches = [5,0,0]
        return
    if switch in ('100',1):
        collector_switches = [0,5,0]
        return
    if switch in ('10',2):
        collector_switches = [0,0,5]
        return
    raise ValueError(str(switch) + " is an invalid argument")    

def set_dac0_bin(bin_value):
    if not (bin_value in range(4096)):
        raise ValueError(str(bin_value) + " is not a valid argument")
    voltage = round( bin_value*5.0/4096, 6)
    global dac0; dac0 = voltage
    return voltage

def set_dac1_bin(bin_value):
    if not (bin_value in range(4096)):
        raise ValueError(str(bin_value) + " is not a valid argument")
    voltage = round( bin_value*5.0/4096, 6)
    global dac1; dac1 = voltage
    return voltage

def check_switches():
    if not(switch_check):
        return
    global base_switches; global collector_switches;
    if not(collector_switches in [[5,0,0] , [0,5,0] , [0,0,5]]):
        raise ValueError("the collector switches are incorrect")
    if not(base_switches in [[5,0] , [0,5]]):
        raise ValueError("the base switches are incorrect")            

def get_dataset():
    ''' gets all the measurements in the dataset, regardless on whether they exist in the database
or not.
returns them as a list of dictionaries'''
    dataset = open(dataset_file, 'r')
    data = dataset.read()
    dataset.close()
    dataset_variables = [i.strip('\n') for i in data.split("###\n")[0].strip('\n').split('\n')]
    check_dataset_variables(dataset_variables)
    data = [point.split('\n') for point in data.split("###\n")[1:]]
    dataset_list = []
    for point in data:
        measurement = {}
        for i in range(len(dataset_variables)):
            measurement[dataset_variables[i]] = float(point[i])
        dataset_list.append(measurement)
    return dataset_to_database_format(dataset_list)

def dataset_to_database_format(dataset):
    '''gets a list of dictionaries (each dictionary being a point) and returns it in the database
format {(dac0_bin, dac1_bin, base_switch, collector_switch) : {point}}'''
    dataset_dict = {}
    for point in dataset:
        dac0_bin = int(round(point['dac0']*4096/5,0))
        dac1_bin = int(round(point['dac1']*4096/5,0))
        b_switches = [int(round(voltage,0)) for voltage in [point['sw_b0'], point['sw_b1']]]
        c_switches = [int(round(voltage,0)) for voltage in [point['sw_c0'], point['sw_c1'], point['sw_c2']]]

        if not(c_switches in [[5,0,0] , [0,5,0] , [0,0,5]]):
            raise ValueError("the collector switches in point " + str(dataset.index(point)) + \
                             " in the dataset are incorrect: " + str(c_switches))
        if not(b_switches in [[5,0] , [0,5]]):
            raise ValueError("the base switches in point " + str(dataset.index(point)) + \
                             " in the dataset are incorrect: " + str(b_switches))

        b_switch_num = b_switches.index(5)
        c_switch_num = c_switches.index(5)
        index = (dac0_bin, dac1_bin, b_switch_num, c_switch_num)
        dataset_dict[index] = point
    return dataset_dict

def check_dataset_variables(dataset_variables):
    ''' checks whether the dataset variables are identical to the user-defined variables '''
    user_variables = [var.user_name for var in read_user_variables()]
    if user_variables != dataset_variables:
        raise ValueError("user variables are different from dataset variables")

def write_dataset(dataset_file):
    ''' writes the entire database into a new dataset.
any existing file with the same name will be lost'''
    file = open(dataset_file, 'w')
    file.writelines([var + '\n' for var in list(database[list(database.keys())[0]].keys())])
    for point in database.values():
        file.write("###\n")
        file.writelines([str(measurement) + '\n' for measurement in point.values()])
    file.close()

def update_dataset(new_data, dataset_file):
    '''adds a list of results (new_data) to the dataset file, maintaining existing data'''
    t = time.perf_counter()
    file = open(dataset_file, 'a')
    for point in new_data:
        file.write("###\n")
        file.writelines([str(measurement) + '\n' for measurement in point.values()])
    file.close()
    print("dataset updated in", round(time.perf_counter() - t,1), "s")
        
def load_dataset():
    '''loads the dataset into the database'''
    global database;
    t = time.perf_counter()
    database = get_dataset()
    print("database loaded in", round(time.perf_counter() - t,1),\
          "s.", len(database), "simulations")

def wait_for_simulation():
    os.chdir("C:\\Users\\mizra\\Desktop\\madNUN")
    cmd_output = os.popen("dir /-c").read()
    file_name_index = cmd_output.index(file_name.strip(".cir") + ".raw")
    cmd_output = cmd_output[ : file_name_index].split(' ')
    file_size = int(cmd_output[-2])

def update_database(results):
    global database
    existing_data = database.keys()
    new_data = []
    for result in results:
        base_switch = [round(result['sw_b0'],0), round(result['sw_b1'],0)].index(5.0)
        collector_switch = [round(result['sw_c0'],0), round(result['sw_c1'],0), round(result['sw_c2'],0)].index(5.0)
        dac0_r = int( round(result['dac0']*4096/5,0) )
        dac1_r = int( round(result['dac1']*4096/5,0) )
        if not( (dac0_r, dac1_r, base_switch, collector_switch) in existing_data ):
            database[(dac0_r, dac1_r, base_switch, collector_switch)] = result
            new_data.append(result)
    return new_data

def fish_result():
    global database
    global collector_switches; global base_switches;
    global dac0; global dac1;
    voltage_to_bin = lambda voltage: int( round(voltage*4096/5, 0) )
    if (voltage_to_bin(dac0), voltage_to_bin(dac1), base_switches.index(5), collector_switches.index(5)) in database.keys():
        return database[(voltage_to_bin(dac0), voltage_to_bin(dac1), base_switches.index(5), collector_switches.index(5))]
    else:
        return False

def simulate(jump = 1):
    result_in_database = fish_result()
    if result_in_database != False:
            return result_in_database

    if forward_sim == True:
            create_simulation(jump = jump, sweep = 'dac0')
            run_simulation()
            measurements = read_user_variables()
            results = read_sim_results(measurements)
            new_results = update_database(results)
            create_simulation(jump = jump, sweep = 'dac1')
            run_simulation()
            results = read_sim_results(measurements)
            new_results += update_database(results)
            update_dataset(new_results, dataset_file)
            #write_dataset(dataset_file)
            return fish_result()
            
    create_simulation(jump)
    run_simulation()
    measurements = read_user_variables()
    results = read_sim_results(measurements)
    update_database(results)
    return fish_result()

def dac1_bin():
    global dac1
    return int(round(dac1*4096/5,0))

def dac0_bin():
    global dac0
    return int(round(dac0*4096/5,0))

print("starting simulation")
load_dataset()
set_base_switches('100')
set_collector_switches('10')
set_dac0_bin(4095)
set_dac1_bin(0)



    
