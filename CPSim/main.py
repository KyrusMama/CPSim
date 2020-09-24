import Interpreter
import numpy as np
import matplotlib.pyplot as plt
import time
import saver
import threading
import xlsxwriter as xw


n_plots = 0


def raster():
    # plots a raster plot (spike timing plot) for all neurons. colors different groups different colors
    fires = [np.greater(np.array(all_neurons[i].output_history), 0.1) for i in range(total_neuron_number)]
    fire_times = [[j for j in range(len(fires[i])) if fires[i][j]] for i in range(total_neuron_number)]
    fig, axs = plt.subplots(1, 1)
    axs.eventplot(fire_times, linelengths=0.5, colors="black")
    plt.ylabel("Neuron number")
    plt.xlabel("timestep")
    plt.title("raster")


def sub_raster(neurons, times):
    fires = [np.greater(np.array(neurons[i].output_history), 0.1) for i in range(len(neurons))]
    fire_times = [[j for j in range(len(fires[i])) if fires[i][j]] for i in range(len(neurons))]
    fire_times = [[t for t in ts if t in times] for ts in fire_times]
    if not_first_plot:
        plt.figure()
    fig, axs = plt.subplots(1, 1)
    axs.eventplot(fire_times, linelengths=0.5, colors="black")
    plt.ylabel("Neuron")
    plt.xlabel("timestep")
    plt.title("raster")


def plt_subspec(val_lst, times, use_name):
    v = np.zeros(final_timestep)

    for vs in val_lst:
        v += vs
    v = v[times]
    # f, t, Sxx = signal.spectrogram(x/100, fs = 1000)
    # plt.pcolormesh(t, f, Sxx, shading='gouraud')
    nfft = 100
    noverlap = 85
    if not_first_plot:
        plt.figure()
    plt.specgram(v/len(val_lst), Fs=1000./timestep, NFFT=nfft, noverlap=noverlap)
    plt.xlabel('Time[s]')
    plt.ylabel('Frequency[Hz]')
    plt.title('Spectrogram of '+use_name)
    plt.ylim((0, 150))
    plt.tight_layout(pad=1.5)


def save_data_file(X, Y, X_unit, name, nos, keyword, func, use_name, ids=None):
    """
    neuron: list of neuron types desired
    indices: tuple/list of tuples that indicates the starting and ending neurons
    times: tuple of start and end times of recording

    writes data into an excel file
    """

    workbook = xw.Workbook(name + ".xlsx")
    worksheet = workbook.add_worksheet()

    row_number, col_number = 0, 0
    title = "The following data is "+func+" of "+keyword+" from "+nos+"s "+use_name
    comment1 = "Row headers are "+nos+" and their indices."
    comment2 = "Column headers are "+X_unit
    worksheet.write(row_number, col_number, title)
    row_number += 1
    worksheet.write(row_number, col_number, comment1)
    row_number += 1
    worksheet.write(row_number, col_number, comment2)

    row_number, col_number = 4, 1
    for xi in range(len(X)):
        worksheet.write(row_number, col_number, X[xi])
        col_number += 1

    row_number, col_number = 5, 0
    for i in range(len(Y)):
        if ids is not None and len(ids) >= len(Y):
            worksheet.write(row_number, col_number, str(ids[i]))
        for t in range(len(X)):
            col_number += 1
            worksheet.write(row_number, col_number, Y[i][t])
        col_number = 0
        row_number += 1
    workbook.close()
    print("excel file saved")


def apply_func(app_func, value_list, times):
    if app_func == "raw":
        return times, [values_in[times] for values_in in value_list], "ms"
    elif app_func == "mean":
        value_list = [np.expand_dims(values_in, 1) for values_in in [values_in[times] for values_in in value_list]]
        value_arr = np.concatenate(value_list, axis=1)
        value_arr = np.mean(value_arr, axis=1)
        return times, [value_arr], "ms"
    elif app_func == "psd":
        value_list = [np.expand_dims(values_in, 1) for values_in in [values_in[times] for values_in in value_list]]
        value_arr = np.concatenate(value_list, axis=1).transpose()
        ff = np.power(np.abs(np.fft.fft(value_arr, axis=1)), 2)
        omega = np.fft.fftfreq(len(times), timestep/1000)
        ff = ff[:, :omega.shape[0]//2]
        omega = omega[:omega.shape[0] // 2]
        nd = np.argmin(np.abs(omega - 200))
        return omega[:nd], ff[:nd], "Hz"
    elif app_func == "mean_psd":
        value_list = [np.expand_dims(values_in, 1) for values_in in [values_in[times] for values_in in value_list]]
        value_arr = np.concatenate(value_list, axis=1).transpose()
        ff = np.power(np.abs(np.fft.fft(value_arr, axis=1)), 2)
        omega = np.fft.fftfreq(len(times), timestep/1000)
        ff = ff[:, :omega.shape[0]//2]
        omega = omega[:omega.shape[0] // 2]
        ff = np.mean(ff, axis=0)
        nd = np.argmin(np.abs(omega - 200))
        return omega[:nd], [ff[:nd]], "Hz"


def simplify_plot(X, Y, X_unit, name):
    rows = int(np.sqrt(len(Y)))
    cols = int(np.ceil(len(Y)/rows))
    if not_first_plot:
        plt.figure()
    plt.title(name+" with x-axis unit="+X_unit)
    for i in range(len(Y)):
        ax = plt.subplot(rows, cols, i+1)
        plt.plot(X, Y[i])


def generate_save_or_plot(line=-1):
    try:
        ttu = Interpreter.get_save_selection(line)
    except KeyError:
        print("Error: there was an issue with the given input. (A neuron/synapse group name was probably wrong).")
        ttu = None
    rv = 1
    if ttu == "end":
        return 0
    elif ttu is None:
        pass
    else:
        sop, nos, val_type, func, object_list, times, use_name = ttu
        if func == "raster" and sop == "plot" and nos == "neuron":
            sub_raster(object_list, times)
            rv = 2
        elif func == "raster":
            print("incorrect use of raster (must be plot and neuron), please consult manual")
        else:
            try:
                val_lst = [x.printable_dict[val_type] for x in object_list]
                if func == "spectrogram" or func == "spec" and sop == "plot":
                    plt_subspec(val_lst, times, use_name)
                    return 2
                elif func == "spectrogram" or func == "spec":
                    print("Error: spectrogram can only be plotted")
                else:
                    rt = apply_func(func, val_lst, times)
                    if rt is None:
                        print("invalid func: recommend trying \"raw\" or \"mean\"")
                        return 1
                    X, Y, X_unit = rt
                    title = "" + func + " of " + nos + "s " + val_type + " for " + use_name
                    if sop == "plot":
                        simplify_plot(X, Y, X_unit, title)
                        print("here")
                        return 2
                    elif sop == "save":
                        if nos == "neuron":
                            ids = [n.id for n in object_list]
                        else:
                            ids = [(s.pre.id, s.post.id) for s in object_list]
                        title = "" + func + " of " + nos + "s " + val_type
                        print("saving...")
                        save_data_file(X, Y, X_unit, title, nos, val_type, func, use_name, ids=ids)

            except KeyError:
                print("invalid keyword")
    return rv


if __name__ == "__main__":
    seed = 2
    pn = 3

    # get model file name from metadata.txt or from console
    file = Interpreter.get_filename()

    # building or loading model
    vals = Interpreter.interpret_file(file)
    timestep, _, total_neuron_number, all_neurons, neuron_dict, group_names, all_connections, \
        connection_dict, connection_names, external_inputs, sniff_frequency, nclass_dict, save_info\
        = vals
    load_dir, keep_load, save_dir = save_info

    starting_timestep, final_timestep = saver.load_data(vals)
    print("external inputs", external_inputs)
    print(timestep)

    for neuron in all_neurons:
        neuron.update_starting_parameters(load_dir == "")
    for synapse in all_connections:
        synapse.update_starting_parameters(load_dir == "")

    # running model
    time_taken = []
    pps = -5
    for t in range(starting_timestep, final_timestep):

        s = time.time()
        for neuron in all_neurons:
            if (neuron.id, t) in external_inputs:
                # if neuron.id == 75:
                #     print(t, external_inputs[(neuron.id, t)])
                neuron.update_voltage(t, timestep, external_inputs[(neuron.id, t)])
            else:
                neuron.update_voltage(t, timestep, 0)
        for synapse in all_connections:
            synapse.update_weights(t, timestep)
        time_taken.append(time.time() - s)
        if t - pps > (final_timestep//100):
            print("step number:", t,
                  "\tpercent done:",
                  np.round((100.0 * (t - starting_timestep + 1)) / (final_timestep - starting_timestep + 1), 2),
                  "\ttime per step estimate:",
                  np.round(np.mean(time_taken[max(0, len(time_taken) - 10):len(time_taken)]), 3),
                  "\ttime estimate:",
                  np.round(np.mean(time_taken[max(0, len(time_taken) - 50):len(time_taken)]) * (final_timestep - t), 1))

    # make save
    saver.save(vals)

    # make predefined data plots or saves
    not_first_plot = False
    print(Interpreter.predef_output_lines)
    ret = 1
    any_plots = False
    for line in Interpreter.predef_output_lines:
        ret = generate_save_or_plot(line)
        if ret == 0:
            break
        if ret == 2:
            not_first_plot = True
            any_plots = True

    if any_plots:
        print("You must close the plots to progress to user inputs")
        plt.show()

    # make user defined plots
    while ret:
        ret = generate_save_or_plot()
        if ret == 2:
            not_first_plot = True
            print("You must close the plot to continue to enter user inputs")
            plt.show()

