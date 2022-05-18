import enum


T = 60
transmit = 0.01


# состояния событий
class State(enum.Enum):
    ARRIVAL = 1     # есть пакет на отправку
    SEND = 2        # освободился канал передачи


class Event:
    def __init__(self, state_, time_, packet_, number_):
        self.state = state_             # тип события ARRIVAL или SEND
        self.time = time_               # время наступления события
        self.packet = packet_           # 0 - если пакета на отправку нет, или пакет для передачи
        self.switch_number = number_    # номер коммутатора, на котором произошло событие


class Packet:
    def __init__(self, size_p, sls, start_t, slice_):
        self.size = size_p          # размер пакета
        self.slice_number = sls            # номер слайса, которому принадлежит пакет
        self.begin_time = start_t   # время поступления пакета в сеть
        self.virtual_end_time = 0   # виртуальное время окончания отправки пакета на коммутаторе
        self.slice = slice_           # поток, которому принадлежит пакет


class Slice:
    def __init__(self, number_, packet_size_, bandwidth_, delay_, estimate_, alpha_, beta_, path_):
        self.number = number_            # номер слайса
        self.packet_size = packet_size_  # размер поступающих пакетов
        self.bandwidth = bandwidth_      # пропускная способность слайса
        self.qos_delay = delay_          # требуемая задержка
        self.estimate_delay = estimate_  # математическая оценка задержки
        # self.flows_list = list()         # список маршрутов

        self.alpha = alpha_  # интенсивность почтупления пакетов (параметр Пуассона)
        self.beta = beta_
        self.path = path_  # список коммутатор, через которые проходит поток


class Queue:
    def __init__(self, priority_, number_, weight_, slice_):
        self.number = number_           # номер очереди
        self.weight = weight_           # вес очереди
        self.buffer = list()            # буфер с пакетами
        self.priority = priority_       # приориет
        self.slice = slice_             # слайс, которой передает в этой очереди
        self.virt_finish_send_time = 0  # время окончания отправки последнего пакета из этой очереди

    # получение текущей заполненности буфера
    def size_of(self):
        return len(self.buffer)

    # получение пакета из очереди
    def pop(self):
        return self.buffer.pop(0)

    # положить пакет в очередь
    def push(self, packet):
        self.buffer.append(packet)


class VirtualTime:
    B_j = set()         # множество непустых очередей - B_j
    prev_virt_time = 0  # виртуальное время предыдущего изменения непустых очередей - V(t_{j-1})
    phys_time = 0       # физическое время изменения непустых очередей - t_{j-1}


class Switch:
    def __init__(self, id_, bandwidth_):
        self.id = id_                       # идентификатор коммутатора
        self.queues_info = dict()           # очереди на коммутаторе
        self.queues_send = list()           # пакеты на отправку, расположенные по приоритетам
        self.bandwidth = bandwidth_         # пропускная способность канала
        self.link_state = True              # состояние канала (занят передачей или свободен)
        self.slice_distribution = dict()    # соответствие слайсов и очередей
        self.next_switches = []             # следующие коммутаторы, на которые может быть отправлен пакет
        self.queue_priority_distr = dict()  # каждому приоритету соответствуют номера очередей, имеющие этот приоритет
        self.virt_time_param = dict()       # параметры виртуального времени (B_j, V(t_{j-1}), t_{j-1})

    # положить пакет в буфер очереди, которая закреплена за этим слайсом
    def push_packet_to_queue(self, queue_number, packet, in_time):
        # получаем приоритет очереди на отправку
        priority = self.queues_info[queue_number].priority
        # вычисляем вируальное время окончания отправки
        virtual_finish_time = self.calculate_virtual_end_time(self.queues_info[queue_number], packet, priority, in_time)
        # сохраняем виртуальное время отправки последнего пакета из этой очереди
        self.queues_info[queue_number].virt_finish_send_time = virtual_finish_time
        # добавляем пакет в нужное место в списке ожидания на отправку
        packet.virtual_ebd_time = virtual_finish_time
        pos = 0
        for elem in self.queues_send[priority - 1]:
            if elem.virtual_end_time < virtual_finish_time:
                pos += 1
            else:
                break
        self.queues_send[priority - 1].insert(pos, packet)
        self.queues_info[queue_number].buffer.append(packet)

    # получить пакет на передачу из первой непустой очереди
    def get_packet_for_transmit(self):
        for queue in self.queues_send:
            if len(queue) != 0:
                packet = queue.pop(0)
                self.queues_info[self.slice_distribution[packet.slice_number]].pop()
                return packet
        return 0

    # вычисляем виртуальное время окончания отправки пакета
    def calculate_virtual_end_time(self, queue, packet, priority, in_time):
        weight = 0
        tau = in_time - self.virt_time_param[priority].phys_time
        #print(self.virt_time_param[priority].B_j)
        for number in self.virt_time_param[priority].B_j:
            #print("number :", number, "queue_info :", self.queues_info)
            #print(self.queues_info.keys())
            if number in self.queues_info.keys():
                weight += self.queues_info[number].weight
        if weight == 0:
            weight = 1
        virtual_time = self.virt_time_param[priority].prev_virt_time + tau / weight
        start_time = max(queue.virt_finish_send_time, virtual_time)  # max(F_i^(k-1), V(phisical_time_i))
        finish_time = start_time + packet.size / queue.weight
        return finish_time

    def check_virtual_time_correct(self, queue_number, curr_time):
        priority = self.queues_info[queue_number].priority
        # print("priority :", priority)
        same_priority_queues = self.queue_priority_distr[priority]
        # print("same_priority_queues :", same_priority_queues)
        not_empty = set()
        for number in same_priority_queues:
            if self.queues_info[number].size_of() != 0:
                not_empty.add(number)

        if not self.virt_time_param[priority].B_j == not_empty:
            weight = 0
            for number in self.virt_time_param[priority].B_j:
                # print("number :", number, "queue_info :", self.queues_info)
                if number in self.queues_info.keys():
                    weight += self.queues_info[number].weight
            if weight == 0:
                weight = 1
            self.virt_time_param[priority].prev_virt_time += \
                (curr_time - self.virt_time_param[priority].phys_time) / weight
            self.virt_time_param[priority].phys_time = curr_time
            self.virt_time_param[priority].B_j.clear()
            self.virt_time_param[priority].B_j.update(not_empty)


class Time:
    def __init__(self):
        self.time_list = list()     # список событий
        self.pos = 0                # текущее положение указателя в списке событий

    # получить событие, которое находится по позиции pos
    def get_time(self):
        if self.pos == len(self.time_list):
            return 0
        event = self.time_list[self.pos]
        self.pos += 1
        return event

    # добавить новое событие в порядке возрастания времени
    def add_event(self, ev):
        i = 0
        if len(self.time_list) == 0:
            self.time_list.append(ev)
            return
        while i < len(self.time_list):
            if ev.time > self.time_list[i].time:
                i += 1
            else:
                break
        self.time_list.insert(i, ev)


class Statistics:
    def __init__(self, slices, topology):
        self.delay = dict()
        self.data_volume = dict()
        self.throughput = dict()
        for key in slices.keys():
            self.delay[key] = list()
        for sw in topology.keys():
            self.data_volume[sw] = dict()
            self.throughput[sw] = dict()
            for sls in slices.keys():
                self.data_volume[sw][sls] = 0
                self.throughput[sw][sls] = list()
