import json
import yaml
file = open("tmp/cal_286.json","r")
calibrado = json.load(file)
valores = [p["valor"] for p in calibrado["parametros"]]
boundary_names = ["input_1","input_2"]
n = valores[0]
m = valores[1]
N = valores[2]
# (len(calibrado["parametros"]) - 3)
coefficients = list()
index = 3
for i in range(n):
    step = {
        "intercept": valores[index],
        "step": i
    }
    index = index + 1
    step["boundaries"] = list()
    for j in range(N):
        step["boundaries"].append({
            "name": boundary_names[j],
            "values": valores[index:index+m]
        })
        index = index + m
    coefficients.append(step)

yaml.dump(coefficients,open("tmp/286_coefficients.yml","w"))