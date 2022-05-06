import time
import sys
import json



# парсим входной файл
def parse_config(argv, slices, topology):
    # print('Start parsing input file')
    with open(argv[0]) as json_file:
        data = json.load(json_file)

        # считываем слайсы
        slices_data = data['slices']
        for sls in slices_data:
            flow = sls['flow']
            one_slice = Slice(sls['sls_number'], sls['packet_size'], sls['bandwidth'],
                              sls['qos_delay'], sls['estimate_delay'], flow['alpha'], flow['beta'], flow['path'])

            slices[one_slice.number] = one_slice

        # заполняем топологию
        for sw in data['topology']['switches']:
            one_switch = Switch(sw['number'], sw['bandwidth'])

            # считываем очереди
            for qu in sw['queues']:
                one_queue = Queue(qu['priority'], qu['queue_number'], qu['weight'], slices[qu['slice']])
                # заполняем соответствие "слайс" - "очередь"
                one_switch.slice_distribution[qu['slice']] = one_queue.number
                # добавляем словарь с очередями "номер очереди" - "очередь"
                one_switch.queues_info[one_queue.number] = one_queue
                # добавляем информацию о приоритетах очередей: "приоритет" - "очередь"
                one_switch.queue_priority_distr.setdefault(one_queue.priority, [])
                one_switch.queue_priority_distr[one_queue.priority].append(one_queue.number)
                one_switch.virt_time_param[one_queue.priority] = VirtualTime()
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



def main(argv):
    start_time = time.time()
    slices = dict()
    topology = dict()

    # парсим конфиг файл и заполняем необходимы структуры
    parse_config(argv, slices, topology)


if __name__ == "__main__":
    main(sys.argv[1:])