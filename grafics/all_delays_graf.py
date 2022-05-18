# соотношение трех видов задержек (qos_delay, estimate_delay, simulation_delay) для 10-ти слайсов
import matplotlib.pyplot as plot
from math import fabs

file = open("result2", 'r')
text = file.readlines()

x = [t for t in range(1,11)]
res_qos = [0.0 for m in range(1, 11)]
res_math_GG1 = [0.0 for j in range(1, 11)]
res_math_MG1 = [0.0 for h in range(1, 11)]
res_sim = [0.0 for k in range(1, 11)]

i = 0
index=1
while i < len(text) - 1:
    sim_str = text[i].split()
    qos_str = text[i+1].split()
    math_str_GG1 = text[i+2].split()
    math_str_MG1 = text[i + 3].split()
    print(int(sim_str[3]), float(sim_str[len(sim_str) - 1]))
    res_sim[int(sim_str[3]) - 1] = float(sim_str[len(sim_str) - 1])
    res_qos[int(sim_str[3]) - 1] = float(qos_str[len(qos_str) - 1])
    res_math_GG1[int(sim_str[3]) - 1] = (float(math_str_GG1[len(math_str_GG1) - 1]))
    res_math_MG1[int(sim_str[3]) - 1] = (float(math_str_MG1[len(math_str_MG1) - 1]))
    i += 6
    index += 1


fig, ax = plot.subplots()
plot.title('Соотношения задержек для 10-ти виртуальных пластов')
plot.xlabel('Номер виртуального пласта')
plot.ylabel('Задержка, (с)')
#ax.plot(x, res_qos, c='g', linestyle='--', marker='.', label='Требование задержки')
#ax.plot(x, res_math_GG1, c='r', linestyle='-', marker='.', label='Математическая оценка задержки GG1')
ax.plot(x, res_math_MG1, c='c', linestyle='-', marker='.', label='Математическая оценка задержки MG1')
ax.plot(x, res_sim, c='b', linestyle=':', marker='.', label='Задрежка симуляции')
ax.legend(loc='best')
#ax.axvline(x=6.5, c='red', linestyle='--')
#ax.axvline(x=13.5, c='red', linestyle='--')
plot.savefig('all_delays_graf12.png', dpi=300, bbox_inches='tight')
plot.show()
