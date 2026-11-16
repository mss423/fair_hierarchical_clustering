from utils import calculate_distance, convert_dist, average_linkage, update_colors, update_counts, print_tree_color
from utils import order_children, MakeFair, get_balances, get_balances_at, print_tree, tree_cost
from eps_local_opt_fairlet import load_data_with_color
from helper_functions_gen import subsample
import matplotlib.pyplot as plt
import seaborn as sns
from copy import deepcopy
import numpy as np
import os.path
import math
import time
import random

n = 512
save_path = ""

# LOAD DATA INTO NUMPY ARRAY
filename = "adult.csv"
# filename = "bank.csv"
# data_bal = 6/7
data_bal = 1/3
blue_points, red_points = load_data_with_color(filename)
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

filename = os.path.join(save_path, "cost_experiment_output_bank.txt")
text_file = open(filename, "w")

# COLLECT CLUSTER STATISTICS OF AVG LINK
# pre_balance = np.sort(get_balances(root))
# fig, axs = plt.subplots(figsize=(4,4))
# axs.hist(pre_balance, bins=10, density=1)
# # axs.hist(pre_balance, density=1)
# axs.axvline(x=data_bal, color='r')
# axs.set_xlim([0,2*(data_bal)])
# plt.savefig(os.path.join(save_path, "avg_link_clusters.png"))

print(" Time taken was %s seconds" % lkg_end)
avg_lkg_cost = tree_cost(root,simi)
# avg_lkg_cost = 1
text_file.write(" --- Cost of average linkage tree = %s --- \n" % avg_lkg_cost)
print(" --- Running fair hierarchical clustering for various parameters... ---")

# ============================================================================================================= #
# RUN FAIR CLUSTERING ALGORITHMS

c = 2
eps = 1 / (c * math.log2(n)) # 1/16
# print(eps)
h = 4
k = 2

order_children(root)

start_time = time.time()

MakeFair(root, h, k, eps, blue_ids, red_ids)
# print_tree_color(root)

end_time = time.time() - start_time
# pointer_patch(root)

pre_balance = np.sort(get_balances(avg_linkage))
print(" --- Finished algorithm with parameters (c,h,k) = (%d,%d,%d) in %s seconds --- \n" % (c,h,k,end_time))
if k > 1:
    post_balance = np.sort(get_balances_at(root, math.log2(k)))
else:
    post_balance = np.sort(get_balances(root)) - offset

# fig, axs = plt.subplots(figsize=(4,4))
# axs.hist(post_balance, bins=5, facecolor='#2ab0ff', edgecolor='#169acf', linewidth=0.5, alpha=0.7)#density=1)
# axs.axvline(x=data_bal, color='r')
# axs.set_xlim([0,2*data_bal])
save_name = "average_linkage_bank.png"
# plt.xlabel('Cluster Balance')
# plt.ylabel('Frequency')
# plt.savefig(os.path.join(save_path, save_name))

sns.set(font_scale=1.5)

hist_plot = sns.distplot(pre_balance, hist=True, kde=True, rug=False) #, norm_hist=True)
hist_plot.set_xlim([0,2*data_bal])
hist_plot.set(xlabel='Cluster Balance', ylabel='Frequency')
hist_plot.axvline(x=data_bal, color='r')
fig = hist_plot.get_figure()
fig.savefig(os.path.join(save_path, save_name),bbox_inches="tight")
plt.close()

# fig, axs = plt.subplots(figsize=(4,4))
# axs.hist(pre_balance, bins=5, facecolor='#2ab0ff', edgecolor='#169acf', linewidth=0.5, alpha=0.7)#density=1)
# axs.axvline(x=data_bal, color='r')
# axs.set_xlim([0,2*data_bal])
save_name = "post_" + "c=" + str(c) + "_h=" + str(h) + "_k=" + str(k) + "_bank.png"
# plt.xlabel('Cluster Balance')
# plt.ylabel('Frequency')
# plt.savefig(os.path.join(save_path, save_name))

hist_plot = sns.distplot(post_balance, hist=True, kde=True, rug=False) #, norm_hist=True)
hist_plot.set_xlim([0,2*data_bal])
hist_plot.set(xlabel='Cluster Balance', ylabel='Frequency')
hist_plot.axvline(x=data_bal, color='r')
fig = hist_plot.get_figure()
fig.savefig(os.path.join(save_path, save_name),bbox_inches="tight")

fair_cost = tree_cost(root, simi)
rel_cost = fair_cost / avg_lkg_cost

text_file.write(" --- Raw Cost of FairHC tree = %s --- \n" % fair_cost)
text_file.write(" --- Relative Cost of FairHC tree = %s --- \n" % rel_cost)

text_file.close()
print("Finished run.")
