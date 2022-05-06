import math
import scipy.stats as sps


class Flow:
    def __init__(self, number_, eps_, alpha_, beta_, path_):
        self.number = number_  # номер потока
        self.rho_a = 0.0  # скорость поступления трафика (для кривой нагрузки)
        self.b_a = 0.0  # всплеск трафика (для кривой нагрузки)
        self.epsilon = eps_  # вероятность ошибки оценки кривой нагрузки
        self.path = path_  # список коммутатор, через которые проходит поток
        self.alpha = alpha_
        self.beta = beta_


class Slice:
    def __init__(self, id_, throughput_, delay_, packet_, eps_, alpha_, beta_, path_):
        self.id = id_                       # номер слайса
        self.qos_throughput = throughput_   # требования к пропускной способности слайса
        self.qos_delay = delay_             # требования к задержке слайса
        self.estimate_delay = 0.0           # оценка задержки
        self.packet_size = packet_          # размер пакетов, передаваемых в слайсе
        self.packet_size_std = 0.0
        self.sls_sw_set = set()             # множество коммутаторв, через которые проходят потоки слайса
        self.used_sw = set()                # множество коммутаторов из sls_sw_set, на которых уже нельзя изменить qos
        self.leaves = []                    # список всех вершин времен
        self.tree = 0                       # дерево связности времен
        self.route_time_constraints = []    # список временных неравенст для потока
        self.flows_list = [Flow(1, eps_, alpha_, beta_, path_)]

        self.rho_a = 0.0        # скорость поступления трафика (для кривой нагрузки)
        self.b_a = 0.0          # всплеск трафика (для кривой нагрузки)
        self.epsilon = eps_     # вероятность ошибки оценки кривой нагрузки
        self.path = path_       # список коммутатор, через которые проходит поток

        # weibull params
        self.alpha = alpha_
        self.beta = beta_


    def define_distribution(self, stats, rate):
        # вычисляем сколько раз встречается каждое значение x_s
        x_s = dict()
        s = 0
        for st in stats:
            elem = int(float(st[0]))
            if x_s.get(elem, -1) != -1:
                x_s[elem] += 1
            else:
                x_s[elem] = 1
                s += 1

        # находим общее число элементов - sum_n и математическое ожидание sum_xn = sum(x_s * n_s)
        sum_n = sum_xn = 0
        for key in x_s.keys():
            sum_xn += key * x_s[key]
            sum_n += x_s[key]
        lambda_medium = sum_xn / sum_n
        # print('Poisson distribution with lambda = ', lambda_medium)
        # вычисляем вероятность p_s прихода элемента x_s, слагаемое Пирсона K_s и суммарное K
        k_sum = 0
        for key in x_s.keys():
            p_s = lambda_medium ** key / math.factorial(key) * math.exp(-lambda_medium)
            k_s = (x_s[key] - sum_n * p_s) ** 2 / sum_n * p_s
            k_sum += k_s

        self.rho_a = lambda_medium
        sigma_a = 0
        theta = 1000
        self.b_a = sigma_a - 1 / theta * (
                    math.log(self.epsilon) + math.log(1 - math.exp(-theta * (rate - self.rho_a))))


class Queue:
    def __init__(self, number_, slice_, priority_, sw):
        self.number = number_       # номер очереди == номеру слайса
        self.priority = priority_   # приоритет очереди на коммутаторе
        self.weight = 1.0           # доля пропускной способности приоритета (omega)
        self.slice = slice_         # указать на слайс, который передает в этой очереди
        self.rho_s = 0.0            # скорость для кривой обслуживания
        self.b_s = 0.0              # задержка для кривой обслуживания
        self.slice_lambda = self.slice.rho_a

        #self.slice_mu = 0.0

        #self.service_var = self.slice.packet_size_std ** 2

        # arrival
        self.arrival_mean = sps.weibull_min.mean(self.slice.beta, loc=0, scale=self.slice.alpha)
        self.arrival_var = sps.weibull_min.var(self.slice.beta, loc=0, scale=self.slice.alpha)
        self.arrival_scv = self.arrival_var / self.arrival_mean ** 2

        self.service_mean = self.slice.packet_size
        self.service_var = self.slice.packet_size_std ** 2
        self.service_scv = self.service_var / self.service_mean ** 2


class Priority:
    def __init__(self, number_, throughput_, qos_delay_, queue):
        self.priority = number_                     # значение приоритета
        self.throughput = throughput_               # пропускная способность приоритета
        self.queue_list = [queue]                   # список очередей, входящих в приоритет
        self.mean_delay = qos_delay_                # среднее требование по задержка приоритета
        self.delay = 0.0                            # суммарная задержка приоритета
        self.priority_lambda = queue.slice_lambda   # lambda суммарная по всем очередям

        self.priority_mu = (self.throughput / queue.service_mean)
        self.priority_arrival_scv = queue.arrival_scv
        self.priority_service_scv = queue.service_scv
        self.ro = 0.0
        self.sigma_priority = 0.0                   # сумма нагрузок вышестоящих приоритетов
        self.slice_queue = dict()                   # соотношение номер сласа и очереди

    def recalculation(self):
        self.mean_delay = 0.0
        self.priority_lambda = 0.0
        required_throughput = 0.0

        for queue in self.queue_list:
            self.mean_delay += queue.slice.qos_delay
            required_throughput += queue.slice.qos_throughput
            self.priority_lambda += queue.slice_lambda
            self.priority_mu += (self.throughput / queue.service_mean)

        self.mean_delay /= len(self.queue_list)
        for queue in self.queue_list:
            queue.weight = queue.slice.qos_throughput / required_throughput
            queue.rho_s = queue.weight * self.throughput


class Switch:
    def __init__(self, number_, speed_):
        self.number = number_           # номер коммутатора
        self.priority_list = list()     # список приоритетов на коммутаторе
        self.physical_speed = speed_    # физическая пропускная способность канала
        self.remaining_bandwidth = 0.0  # остаточная пропускная способность канала
        self.slice_priorities = dict()  # соотношение номера слайса и его приоритета

