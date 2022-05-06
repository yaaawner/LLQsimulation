def calculate_priority_delay_mg1(topology, sw):
    # вычисляем числитель
    numerator = 0
    for pr in topology.switches[sw].priority_list:
        print(pr.priority_lambda)
        for q in pr.queue_list:
            print(q.slice.packet_size)
        numerator += pr.priority_lambda * (pr.queue_list[0].slice.packet_size ** 2) / (topology.switches[sw].physical_speed ** 2)
    # вычисляем знаменатель
    for i in range(0, len(topology.switches[sw].priority_list)):
        sigma_prev = topology.switches[sw].priority_list[i - 1].sigma_priority
        pr = topology.switches[sw].priority_list[i]
        if pr.priority == 1:
            pr.sigma_priority = pr.priority_lambda / topology.switches[sw].physical_speed
            # if i != 0:
            #     print('pr.priority_lambda =', pr.priority_lambda, 'throughput =', topology.switches[sw].physical_speed)
        else:
            pr.sigma_priority = sigma_prev + pr.priority_lambda / topology.switches[sw].physical_speed
            # if i != 0:
            #     print('sigma_prev =', sigma_prev, 'pr.priority_lambda =', pr.priority_lambda, 'throughput =', topology.switches[sw].physical_speed)
        denominator = 2 * (1 - sigma_prev) * (1 - pr.sigma_priority)
        pr.delay = numerator / denominator

def calculate_queue_delay_mg1(pr):
    # вычисляем сумму минимальных требуемых скоростей для слайсов
    sum_r_k = 0
    for i in range(0, len(pr.queue_list)):
        sum_r_k += pr.queue_list[i].slice.qos_throughput

    for k in range(0, len(pr.queue_list)):
        # вычисляем знаменатель
        lambda_k = pr.queue_list[k].slice_lambda
        r_k = pr.queue_list[k].slice.qos_throughput
        denominator = 1 - (lambda_k * sum_r_k) / (pr.throughput * r_k)
        # print("lambda_k =", lambda_k, "sum_r_k =", sum_r_k, "pr.throughput =", pr.throughput, "r_k =", r_k)
        # вычислем числитель
        numerator = 0.5 * pr.priority_lambda / (pr.throughput ** 2)
        for j in range(0, len(pr.queue_list)):
            if k == j:
                continue
            r_j = pr.queue_list[j].slice.qos_throughput
            l_j = pr.queue_list[j].slice.packet_size
            lambda_j = pr.queue_list[j].slice_lambda
            rho_j = lambda_j * l_j / r_j
            # print('r_j =', r_j, 'l_j =', l_j, 'lambda_j =', lambda_j, 'rho_j =', rho_j)
            numerator += (r_j / r_k + rho_j * l_j) / pr.throughput
        # итоговая задержка для
        # print('numerator =', numerator, 'denominator', denominator)
        pr.queue_list[k].b_s = pr.delay + numerator / denominator