import random
import sys
import scipy.stats as sps

NUMBER = 50000
TIME_INTERVAL = 1


weibull_list = [{"alpha": 0.15, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_1.csv"},
                {"alpha": 0.1, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_2.csv"},
                {"alpha": 0.05, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_3.csv"},
                {"alpha": 0.2, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_4.csv"},
                {"alpha": 0.3, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_5.csv"},
                {"alpha": 0.1, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_6.csv"},
                {"alpha": 0.4, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_7.csv"},
                {"alpha": 0.15, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_8.csv"},
                {"alpha": 0.5, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_9.csv"},
                {"alpha": 0.05, "beta": 0.34, "statistic": "weibull/weibull_2_10_0/weibull_10.csv"}]

def weibull(alpha=0.15, beta=2.0):
    variable_list = []
    #random.seed(1)
    for i in range(0, NUMBER):
        var = random.weibullvariate(alpha, beta)
        variable_list.append(var)
    return variable_list

def convert_to_intensity(variable_list, output_file_name):
    print("mean")
    mean = sum(variable_list)/variable_list.__len__()
    print(mean)

    output_file = open(output_file_name, "w")
    intensity_list = []
    t = 0.0
    count = 0
    current_time = 0
    for var in variable_list:
        t += var
        if t // TIME_INTERVAL == current_time:
            count += 1
        else:
            intensity_list.append(count)
            output_file.write(str(count) + '\n')
            current_time += 1
            while current_time != t // TIME_INTERVAL:
                intensity_list.append(0)
                output_file.write(str(0) + '\n')
                current_time += 1
            count = 1
    intensity_list.append(count)
    output_file.write(str(count) + '\n')
    output_file.close()
    return intensity_list


if __name__ == "__main__":
    for distr in weibull_list:
        print(sps.weibull_min.mean(distr["beta"], loc=0, scale=distr["alpha"]))
        convert_to_intensity(weibull(distr["alpha"], distr["beta"]), distr["statistic"])
