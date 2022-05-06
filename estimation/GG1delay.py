def calculate_priority_delay(topology, sw):
    sigma_prev = 0
    alpha_sum = 0
    beta = 0
    pr_list = topology.switches[sw].priority_list

    for i in range(len(pr_list)):
        pr_list[i].ro = pr_list[i].priority_lambda / pr_list[i].priority_mu

    for R in range(len(pr_list)):
        for i in range(R):
            if i != 0:
                sigma_prev = pr_list[i - 1].sigma_priority
            pr_list[i].sigma_priority = sigma_prev + pr_list[i].ro

            if i != 0:
                alpha_sum += (pr_list[i].ro ** 2) * pr_list[R].priority_lambda * \
                             (pr_list[i].priority_arrival_scv + pr_list[i].priority_service_scv) / pr_list[
                                 i].priority_lambda
            if i != R:
                beta += (pr_list[i].ro ** 2) * pr_list[R].priority_lambda * \
                        (pr_list[i].priority_service_scv + 1) / pr_list[i].priority_lambda

        alpha = pr_list[R].ro * (pr_list[R].priority_service_scv + 1)
        length = pr_list[R].ro + pr_list[R].ro * (pr_list[R].priority_arrival_scv - 1) / (2 * (1 - pr_list[R].sigma_priority)) +\
                 (alpha + beta) / ((1 - pr_list[R].sigma_priority) * (1 - sigma_prev))

        pr_list[R].delay = length / pr_list[R].priority_lambda


def calculate_queue_delay(pr):
    for k in range(0, len(pr.queue_list)):
        numerator = pr.queue_list[k].slice_lambda * (
                pr.queue_list[k].arrival_var + pr.queue_list[k].service_var)
        denominator = 2 * (1 - pr.queue_list[k].slice_lambda / pr.queue_list[k].slice_mu)
        pr.queue_list[k].b_s = pr.delay + numerator / denominator