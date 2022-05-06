import json
import random
import time
import sys

import objects


# парсим входной файл
def parse_config(argv, slices, topology):
    # print('Start parsing input file')
    with open(argv[0]) as json_file:
        data = json.load(json_file)

        # считываем слайсы
        slices_data = data['slices']
        for sls in slices_data:
            flow = sls['flow']
            one_slice = objects.Slice(sls['sls_number'], sls['packet_size'], sls['bandwidth'],
                              sls['qos_delay'], sls['estimate_delay'], flow['alpha'], flow['beta'], flow['path'])

            slices[one_slice.number] = one_slice

        # заполняем топологию
        for sw in data['topology']['switches']:
            one_switch = objects.Switch(sw['number'], sw['bandwidth'])

            # считываем очереди
            for qu in sw['queues']:
                one_queue = objects.Queue(qu['priority'], qu['queue_number'], qu['weight'], slices[qu['slice']])
                # заполняем соответствие "слайс" - "очередь"
                one_switch.slice_distribution[qu['slice']] = one_queue.number
                # добавляем словарь с очередями "номер очереди" - "очередь"
                one_switch.queues_info[one_queue.number] = one_queue
                # добавляем информацию о приоритетах очередей: "приоритет" - "очередь"
                one_switch.queue_priority_distr.setdefault(one_queue.priority, [])
                one_switch.queue_priority_distr[one_queue.priority].append(one_queue.number)
                one_switch.virt_time_param[one_queue.priority] = objects.VirtualTime()
            # заполняем топологию по формату "номер коммутатора" - "коммутатор"
            # print(one_switch.queues_info)
            topology[one_switch.id] = one_switch

        # считываем каналы и устанавливаем связи между коммутаторами
        for lk in data['topology']['links']:
            topology[lk[0]].next_switches.append(lk[1])
            topology[lk[0]].links_state = True
    # формируем виртуальную очередь на отправку пакетов
    create_virtual_send(topology)
    # print('Finish parsing file')


# заполняем все очерди на отправку пустыми списками (подготовка к симуляции)
def create_virtual_send(topology):
    for key in topology.keys():
        sw = topology[key]
        max_queue_priority = 0
        for queue_key in sw.queues_info.keys():
            if sw.queues_info[queue_key].priority > max_queue_priority:
                max_queue_priority = sw.queues_info[queue_key].priority
        for i in range(0, max_queue_priority):
            sw.queues_send.append(list())


def generate_general(slices, event_time):
    print("Start generate")
    for key in slices.keys():
        sls = slices[key]
        packet_count = 1

        t = random.weibullvariate(sls.alpha, sls.beta)
        while t < objects.T:
            # добавляем шейпинг
            if (packet_count * sls.packet_size) / t > sls.bandwidth:
                t += ((packet_count * sls.packet_size / sls.bandwidth) - t)
            # print("sls_number", sls.number, "flow =", flow.path[0], "time = ", t)
            arrival_packet = objects.Packet(sls.packet_size, sls.number, t, sls)
            # добавляем событие в общий список событий
            event_time.add_event(objects.Event(objects.State.ARRIVAL, t, arrival_packet, sls.path[0]))
            # генерируем экспоненциальное значение временного интервала между событиями
            t += random.weibullvariate(sls.alpha, sls.beta)
    print("Finish generate")


# симуляция передачи, пока реализована на одном узле
def simulate(event_time, topology, stat):
    print('simulation')
    # берем первое событие из списка
    event = event_time.get_time()
    while event != 0:
        sw = topology[event.switch_number]
        # если наступило событие окончания передачи пакета, освободи канал
        if event.state == objects.State.SEND:
            # print("\n1 --- Chanel became free in time", event.time, "on switch", sw.id)
            sw.link_state = True
            # print('chanel is free')

        # если пришет новый пакет, размести его в буфере соответствующей очереди
        if event.state == objects.State.ARRIVAL:
            # print("\n2 --- In time", event.time, "on switch", sw.id, "arrived packet with time", event.packet.begin_time)
            # print("sw :", sw.id, "sw.slice_distribution :", sw.slice_distribution, "slice :", event.packet.slice)
            # определяем очередь, которая соответствует данному слайсу
            queue_number = sw.slice_distribution[event.packet.slice_number]
            # добавляем пакет в очередь
            sw.push_packet_to_queue(queue_number, event.packet, event.time)
            # проверям состояние виртулаьного времени
            sw.check_virtual_time_correct(queue_number, event.time)

        # если канал свободен, выполни передачу пакета
        if sw.link_state:
            # достаем пакет из очереди, которая имеет больший приоритет на передачу
            packet = sw.get_packet_for_transmit()
            # если нет пакета на передачу, то переходим к следующему событию
            if packet == 0:
                event = event_time.get_time()
                continue
            # проверям состояние виртулаьного времени
            # print("\n3 --- Send packet in time", event.time, "with time", packet.begin_time, "on switch", sw.id)
            # print("sw :", sw.id, "sw.slice_distribution :", sw.slice_distribution, "slice :", packet.slice)
            sw.check_virtual_time_correct(sw.slice_distribution[packet.slice_number], event.time)
            # вычисляем время окончания отправки пакета
            duration = float(packet.size) / sw.bandwidth
            # print("duration :", duration, ", packet:", packet.size, ", bandwidth :", sw.bandwidth)
            # ставим флаг занятости канала передачи
            sw.link_state = False
            # добавляем новое событие на текущем коммутаторе
            # print("\n4 --- Create new event on sw", sw.id, "packet time", packet.begin_time)
            event_time.add_event(objects.Event(objects.State.SEND, event.time + duration, 0, sw.id))
            # создаем событие на следующем коммутаторе
            next_sw = get_next_switch(packet, sw.id)
            if next_sw != 0:
                # print("\n4 --- Create new event on sw", next_sw, "packet time", packet.begin_time)
                event_time.add_event(objects.Event(objects.State.ARRIVAL, event.time + duration + objects.transmit,
                                                   packet, next_sw))
            else:
                # для каждого слайса сохраняем суммарную задержку в сети
                # print('packet_begin_time =', packet.begin_time)
                stat.delay[packet.slice_number].append(event.time + duration - packet.begin_time)
            # на каждом коммутаторе для каждого слайса сохраняем объем переданных данных
            stat.data_volume[sw.id][packet.slice_number] += packet.size
            # и вычисляем текущую пропускную способность
            stat.throughput[sw.id][packet.slice_number].append(
                stat.data_volume[sw.id][packet.slice_number] / event.time + duration + objects.transmit)
        event = event_time.get_time()
    print('finish simulation\n')


def get_next_switch(packet, sw_number):
    for i in range(0, len(packet.slice.path)):
        if packet.slice.path[i] == sw_number:
            if i == len(packet.slice.path) - 1:
                return 0
            else:
                return packet.slice.path[i+1]
    return 0


def main(argv):
    start_time = time.time()
    slices = dict()
    topology = dict()

    # парсим конфиг файл и заполняем необходимы структуры
    parse_config(argv, slices, topology)

    stat = objects.Statistics(slices, topology)

    # генерируем время прихода пакетов
    event_time = objects.Time()

    generate_general(slices, event_time)

    # выполняем симуляцию отправки пакетов
    simulate(event_time, topology, stat)

    finish_time = time.time() - start_time

    output_file = "gene_out/gene_" + argv[0][4:len(argv[0]) - 5]
    file = open(output_file, 'w')
    for sls in slices.keys():
        print("delay on slice", sls, ':', max(stat.delay[sls]))
        file.write("delay on slice " + str(sls) + " : " + str(max(stat.delay[sls])) + '\n')
        print("required qos delay", sls, ':', slices[sls].qos_delay)
        file.write("required qos delay " + str(sls) + " : " + str(slices[sls].qos_delay) + '\n')
        print("estimate delay :", slices[sls].estimate_delay)
        file.write("estimate delay : " + str(slices[sls].estimate_delay) + '\n')
        print("simulation time :", finish_time)
        file.write("simulation time : " + str(finish_time) + '\n')
        print("-------------------------------------------------")
        file.write("-------------------------------------------------\n")


if __name__ == "__main__":
    main(sys.argv[1:])
