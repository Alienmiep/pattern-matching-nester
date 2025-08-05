from shapely.geometry import Polygon
import matplotlib.pyplot as plt


def plot_polygon(ax, poly, color, label):
    x, y = poly.exterior.xy
    ax.fill(x, y, alpha=0.5, fc=color, ec='black', label=label)


nfp = Polygon([(73.0, 0.0), (120.3, 0.0), (120.3, 58.5), (120.3, 117.0), (47.3, 117.0), (0.0, 117.0), (0.0, 58.5), (0.0, 0.0), (73.0, 0.0)])
poly_1 = Polygon([(0, 0), (0, 91.5), (3.552713678800501e-15, 91.5), (3.552713678800501e-15, 58.5), (3.552713678800501e-15, 0), (0, 0)])
poly_2 = Polygon([(152.7, 91.5), (152.7, 0), (120.3, 0), (120.3, 58.5), (120.3, 91.5), (152.7, 91.5)])



# Set up the plot
fig, ax = plt.subplots()

# Plot polygons
# plot_polygon(ax, nfp, 'blue', 'NFP')
plot_polygon(ax, poly_1, 'green', 'intersection 1')
# plot_polygon(ax, poly_2, 'red', 'intersection 2')

# Misc plot settings
ax.set_aspect('equal')
ax.legend()
ax.grid(True)
plt.title("Polygon NFP Visualization")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()
