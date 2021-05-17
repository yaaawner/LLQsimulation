# время, потраченное на вычисление оценки задержки
import matplotlib.pyplot as plot

x = [a for a in range(1, 21)]
res = [1.1445043087005615,
       0.18041300773620605 + 0.299135684967041,
       0.17868375778198242 + 0.28632283210754395 + 0.47652697563171387,
       0.17516803741455078 + 0.2969644069671631 + 0.47287464141845703 + 0.030218839645385742,
       0.5166099071502686 + 2 * 0.17852282524108887 + 2 * 0.3112039566040039 + 0.05621814727783203 + 0.1729421615600586,
       0.41976404190063477 + 0.1148829460144043 + 0.053574323654174805 + 0.1594703197479248 + 0.1356673240661621 + 0.2797584533691406,
       0.40236687660217285 + 0.0715494155883789 + 0.06350183486938477 + 0.15604805946350098 + 0.06801366806030273 + 0.02138495445251465 + 0.016147851943969727,
       0.4148528575897217 + 0.04138493537902832 + 0.06827783584594727 + 0.06340932846069336 + 0.15620946884155273 + 0.07155895233154297 + 0.020684242248535156 + 0.014864206314086914,
       0.4448883533477783 + 0.0360410213470459 + 0.00922846794128418 + 0.06906652450561523 + 0.0753791332244873 + 0.15833330154418945 + 0.07099032402038574 + 0.019593477249145508 + 0.014704465866088867,
       0.42351484298706055 + 0.3713808059692383 + 0.25725579261779785 + 0.6528596878051758 + 0.06513404846191406 + 0.21872758865356445 + 0.06031060218811035 + 0.6334717273712158 + 0.07746171951293945 + 0.02149343490600586,
       2.735250012366, 3.676513285024, 4.09813743841234, 4.8734281925623, 5.1123846923, 6.2836498125, 8.129836012746512,
       10.184756081451, 14.13478561247, 19.18374174819345]

fig, ax = plot.subplots()
plot.xlabel('Количество заданных виртуальных пластов')
plot.ylabel('Среднее время вычисления оценки задержки, (с)')
ax.plot(x, res, c='green', linestyle=':', marker='.', markersize=10)
# ax.legend(loc='best')
plot.savefig('math_time_graf.png', dpi=300, bbox_inches='tight')
plot.show()
