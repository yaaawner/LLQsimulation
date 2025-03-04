import csv
import json
import math
import sys

import objects, algorithm, mytopology, MG1delay, GG1delay
from objects import MG1_FLAG

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
                                sls_data["packet"], flow["epsilon"], flow["alpha"], flow["beta"], flow["path"])
            #sls.packet_size_std = 0.001

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


# формируем кривую обслуживания на каждом коммутаторе для начальных параметров
def create_start_service_curve(topology):
    # на каждом коммутаторе вычисляем задержку приоритета
    if MG1_FLAG:
        for sw in topology.switches.keys():
            MG1delay.calculate_priority_delay(topology, sw)

        # вычисляем задержку для каждой очереди
        for sw in topology.switches.keys():
            for pr in topology.switches[sw].priority_list:
                MG1delay.calculate_queue_delay(pr)
    else:
        for sw in topology.switches.keys():
            GG1delay.calculate_priority_delay(topology, sw)

        # вычисляем задержку для каждой очереди
        for sw in topology.switches.keys():
            for pr in topology.switches[sw].priority_list:
                GG1delay.calculate_queue_delay(pr)
    # print_queue_organization(topology)


# записываем результаты работы в выходной файл
def write_result(file_name, slices, topology):
    output_file = "out/out" + file_name + ".json"
    file = open(output_file, "w")
    file.write('{\n')
    file.write("\t\"slices\" : [\n")
    # записываем информацию о слайсах
    slice_numbers = len(slices.keys())
    for sls in slices.keys():
        file.write("\t\t{\n \t\t\t\"sls_number\" : " + str(sls) + ",\n")
        file.write("\t\t\t\"packet_size\" : " + str(slices[sls].packet_size) + ",\n")
        file.write("\t\t\t\"bandwidth\" : " + str(slices[sls].qos_throughput) + ",\n")
        file.write("\t\t\t\"qos_delay\" : " + str(slices[sls].qos_delay) + ",\n")
        file.write("\t\t\t\"estimate_delay\" : " + str(slices[sls].estimate_delay) + ",\n")
        file.write("\t\t\t\"flow\" : \n")
        # записываем информацию о потоках
        flow_count = len(slices[sls].flows_list)
        for flow in slices[sls].flows_list:
            file.write("\t\t\t\t{\n")
            file.write("\t\t\t\t\t\"alpha\" : " + str(flow.alpha) + ",\n")
            file.write("\t\t\t\t\t\"beta\" : " + str(flow.beta) + ",\n")
            file.write("\t\t\t\t\t\"path\" : [")
            path_len = len(flow.path)
            for elem in flow.path:
                file.write(str(elem))
                path_len -= 1
                if path_len != 0:
                    file.write(", ")
            file.write("]\n\t\t\t\t}")
            flow_count -= 1
            if flow_count != 0:
                file.write(",\n")
            else:
                file.write("\n")
        file.write("\t\t\t\n\t\t}")
        slice_numbers -= 1
        if slice_numbers != 0:
            file.write(",\n")
    file.write("\n\t],\n \t\"topology\" : { \n \t\t\"switches\" : [\n")
    # записываем информацию о коммутаторах
    sw_numbers = len(topology.switches.keys())
    for sw in topology.switches.keys():
        file.write("\t\t\t{\n \t\t\t\t\"number\" : " + str(sw) + ",\n")
        file.write("\t\t\t\t\"bandwidth\" : " + str(topology.switches[sw].physical_speed) + ",\n")
        file.write("\t\t\t\t\"queues\" : [\n")
        # записываем информацию о каждой очереди
        queues_count = 0
        pr_count = len(topology.switches[sw].priority_list)
        for pr in topology.switches[sw].priority_list:
            pr_count -= 1
            queues_count += len(pr.queue_list)
            for queue in pr.queue_list:
                file.write("\t\t\t\t\t{\n \t\t\t\t\t\t\"priority\" : " + str(pr.priority) + ",\n")
                file.write("\t\t\t\t\t\t\"queue_number\" : " + str(queue.number) + ",\n")
                file.write("\t\t\t\t\t\t\"slice\" : " + str(queue.slice.id) + ",\n")
                file.write("\t\t\t\t\t\t\"weight\" : " + str(queue.weight) + "\n")
                file.write("\t\t\t\t\t}")
                queues_count -= 1
                if pr_count != 0 or queues_count != 0:
                    file.write(",\n")
                else:
                    file.write("\n")
        file.write("\t\t\t\t]\n \t\t\t}")
        sw_numbers -= 1
        if sw_numbers != 0:
            file.write(",\n")
    file.write("\n\t\t],\n \t\t \"links\" : [\n")
    # записываем информацию о каналах
    lk_count = 0
    for lk in topology.links:
        file.write("\t\t\t[" + str(lk[0]) + ", " + str(lk[1]) + "]")
        lk_count += 1
        if lk_count != len(topology.links):
            file.write(",\n")
    file.write("\n\t\t] \n \t}\n }\n")


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

    # формируем кривую обслуживания на каждом коммутаторе для начальных параметров
    create_start_service_curve(topology)

    # подбор корректных параметров для слайсов
    algorithm.modify_queue_parameters(slices, slices_order, topology, file_name)

    # записываем результаты работы в выходной файл
    write_result(file_name, slices, topology)


if __name__ == "__main__":
    main(sys.argv[1:])
