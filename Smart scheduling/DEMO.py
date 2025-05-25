import random
import numpy as np
from scipy.stats import norm

# توزیع احتمال برای روزهای هفته
days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
day_probabilities = [1/22, 1/22, 4/22, 4/22, 4/22, 3/22, 5/22]

def choose_day():
    return random.choices(days, weights=day_probabilities, k=1)[0]

# توزیع احتمال برای ساعات روز (شبه گاوسی با سه قله)
hours = range(24)
minute_intervals = range(0, 60, 1)

time_slots = [f"{h:02d}:{m:02d}" for h in hours for m in minute_intervals]
probabilities = np.zeros(len(time_slots))

# تعریف توابع نرمال برای سه قله
peak_a = norm(loc=21.5, scale=1.5)  # قله در 21:30
peak_b = norm(loc=12.5, scale=1.5)  # قله در 12:30
peak_c = norm(loc=9.0, scale=0.5)  # قله در 09:00

# وزن دهی به قله ها
weight_a = 0.55
weight_b = 0.35
weight_c = 0.1

# محاسبه احتمالات برای هر بازه زمانی
for i, time_str in enumerate(time_slots):
    hour = int(time_str[:2]) + int(time_str[3:]) / 60
    prob_a = weight_a * peak_a.pdf(hour)
    prob_b = weight_b * peak_b.pdf(hour)
    prob_c = weight_c * peak_c.pdf(hour)
    probabilities[i] = prob_a + prob_b + prob_c

# کاهش احتمال برای ساعات 2 تا 7
for i, time_str in enumerate(time_slots):
    hour = int(time_str[:2])
    if 2 <= hour < 7:
        probabilities[i] *= 0.1 # کاهش احتمال به 10% مقدار اولیه

# نرمال سازی احتمالات
probabilities /= np.sum(probabilities)

def choose_time():
    return random.choices(time_slots, weights=probabilities, k=1)[0]
