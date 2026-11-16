from utils import calculate_distance, convert_dist, average_linkage, update_colors, update_counts, print_tree_color
from utils import order_children, MakeFair, get_balances, get_balances_at, print_tree, tree_cost
from eps_local_opt_fairlet import load_data_with_color
from helper_functions_gen import subsample
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from copy import deepcopy
import numpy as np
import os.path
import math
import time
import random

save_path = ""

# LOAD DATA INTO NUMPY ARRAY
filename = "adult.csv"
data_bal = 6/7
blue_points, red_points = load_data_with_color(filename)

c = 2
h = 4
k = 2

ns = [128, 256, 512, 1024, 2048]
counter = 0

for n in ns:
    blue_pts_sample, red_pts_sample = subsample(blue_points, red_points, n)
    data = []
    data.extend(blue_pts_sample)
    data.extend(red_pts_sample)
    data = np.array(data)
    # Note: node ids correspond to index in data list

    num_blue = len(blue_pts_sample)
    num_red  = len(red_pts_sample)
    blue_ids = np.arange(num_blue)
    red_ids  = np.arange(num_blue, num_blue + num_red)

    # BUILD AVERAGE LINKAGE TREE
    dist, _ = calculate_distance(data)
    simi = convert_dist(dist)

    lkg_start = time.time()
    root, _ = average_linkage(simi)
    lkg_end   = time.time() - lkg_start
    update_colors(root, red_ids, blue_ids) # Initialize colors
    avg_linkage = deepcopy(root)
    print(" --- Average linkage tree built! --- ")

    print(" Time taken was %s seconds" % lkg_end)
    avg_lkg_cost = tree_cost(root,simi)
    print(" --- Running fair hierarchical clustering for various parameters... ---")

    order_children(root)
    if n == 128:
        results = pd.DataFrame({"n": n, "cost": avg_lkg_cost}, index=["avg_lkg_0"])
    else:
        temp = pd.DataFrame({"n": n, "cost": avg_lkg_cost}, index=["avg_lkg_" + str(counter)])
        results = results.append(temp)

    eps = 1 / (c * math.log2(n)) # 1/16
    # base_root = deepcopy(root)
    start_time = time.time()

    MakeFair(root, h, k, eps, blue_ids, red_ids)

    end_time = time.time() - start_time

    print(" --- Finished algorithm with parameters (c,h,k) = (%d,%d,%d) in %s seconds --- \n" % (c,h,k,end_time))

    fair_cost = tree_cost(root, simi)
    temp = pd.DataFrame({"n": n, "cost": fair_cost}, index=["fair_" + str(counter)])
    results = results.append(temp)
    counter = counter + 1

results.to_csv(os.path.join(save_path, "cost_experiment_output_vary_n3.csv"))





