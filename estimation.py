import sys
import json
import csv
import math

import mytopology, objects

DELTA_DELAY = 0.8


# парсим конфиг файл и заполняем необходимы структуры
def parse_config(input_file, slices, topology):
    print('Start parsing input file:', input_file)
    with open(input_file) as json_file:
        data = json.load(json_file)

        # считываем топологию
        topo_data = data["topology"]
        for sw_data in topo_data["switches"]:
            sw = objects.Switch(sw_data["number"], sw_data["throughput"])
            topology.switches[sw_data["number"]] = sw
        topology.links = topo_data["links"]

        # считываем слайсы
        for sls_data in data["slices"]:
            correct = True
            flow = sls_data["flow"]
            sls = objects.Slice(sls_data["sls_number"], sls_data["qos_throughput"], sls_data["qos_delay"],
                                sls_data["packet_size"], flow["epsilon"], flow["alpha"], flow["beta"], flow["path"])
            sls.packet_size_std = 0.001

            if "statistic" in flow:
                with open(flow["statistic"], 'r') as f:
                    reader = csv.reader(f)
                    stat_list = list(reader)
                rate = topology.switches[sls.path[0]].physical_speed
                sls.define_distribution(stat_list, rate)
                if sls.rho_a == 0 and sls.b_a == 0:
                    print("Reject slice installation")
                #    correct = False
                #    break
            else:
                sls.rho_a = flow["rho_a"]
                sls.b_a = flow["b_a"]

            slices[sls.id] = sls


# сортируем слайсы в зависимости от требования к задержке
def sort_slices(slices, order):
    for key in slices.keys():
        pos = 0
        for i in range(0, len(order)):
            if slices[order[i]].qos_delay < slices[key].qos_delay:
                pos += 1
            else:
                break
        order.insert(pos, key)


# задаем начальные значения приоритетов и весов для виртуальных пластов на каждом коммутаторе
def set_initial_parameters(slices, slices_order, topology):
    # для каждого слайса создаем множество коммутаторов, через которое проходят потоки
    build_slice_cross_switches_set(slices)

    # для каждоко слайса в порядке slices_order на каждом коммутаторе из sls_sw_set
    # создаем очереди и объединяем их в приоритеты
    create_queue_start_organization(slices, slices_order, topology)
    # print_queue_organization(topology)

    # перераспределем остаточную пропускную способность канала
    flag = mytopology.redistribute_residual_channel_capacity(topology)
    # print_queue_organization(topology)
    return flag


# для каждого слайса создаем множество коммутаторов, через которое проходят потоки
def build_slice_cross_switches_set(slices):
    for sls in slices.keys():
        for sw in slices[sls].path:
            slices[sls].sls_sw_set.add(sw)
        # print(slices[sls].sls_sw_set)


def create_queue_start_organization(slices, slices_order, topology):
    for sls in slices_order:
        for sw in slices[sls].sls_sw_set:
            # создаем очередь для слайса
            queue = objects.Queue(sls, slices[sls], 1, sw)
            if len(topology.switches[sw].priority_list) == 0:
                # создаем приоритет для слайса
                priority = objects.Priority(1, slices[sls].qos_throughput, slices[sls].qos_delay, queue)
                priority.slice_queue[sls] = queue
                queue.rho_s = queue.weight * priority.throughput
                topology.switches[sw].priority_list.append(priority)
                topology.switches[sw].slice_priorities[sls] = priority.priority
            else:
                was_added = False
                for pr in topology.switches[sw].priority_list:
                    if math.fabs(pr.mean_delay - slices[sls].qos_delay) < DELTA_DELAY:
                        was_added = True
                        # добавляем очередь в существующий приоритет
                        queue.priority = pr.priority
                        pr.queue_list.append(queue)
                        pr.slice_queue[sls] = queue
                        pr.throughput += slices[sls].qos_throughput
                        pr.recalculation()
                        topology.switches[sw].slice_priorities[sls] = pr.priority
                if not was_added:
                    # создаем новый приоритет и туда добавляем очередь
                    number = len(topology.switches[sw].priority_list) + 1
                    priority = objects.Priority(number, slices[sls].qos_throughput, slices[sls].qos_delay, queue)
                    priority.slice_queue[sls] = queue
                    queue.rho_s = queue.weight * priority.throughput
                    topology.switches[sw].priority_list.append(priority)
                    topology.switches[sw].slice_priorities[sls] = priority.priority

def main(argv):
    slices = dict()
    topology = mytopology.Topology()

    # парсим конфиг файл и заполняем необходимы структуры
    parse_config(argv[0], slices, topology)

    file_name = argv[0][11:len(argv[0]) - 5]

    # сортируем слайсы в зависимости от требования к задержке
    slices_order = list()  # список номеров слайсов, упорядоченный по возрастанию задержки
    sort_slices(slices, slices_order)

    # задаем начальные значения приоритетов и весов для виртуальных пластов на каждом коммутаторе
    flag = set_initial_parameters(slices, slices_order, topology)
    if flag:
        print('Impossible to continue calculation. Stop working')
        return


if __name__ == "__main__":
    main(sys.argv[1:])
