from shapely.geometry import Polygon, LineString
import matplotlib.pyplot as plt

translation_to_test = LineString([(7.899999999999999, 33.19999999999999), (7.899999999999999, 55.69999999999999)])
target_poly = Polygon([(-27.9, 80.7), (-27.1, 76.9), (-26.7, 73.6), (-26.8, 70.8), (-27.6, 68.4), (-29.3, 66.5), (-32, 65), (-32, 42.5), (-12, 42.5), (8, 42.5), (8, 65), (5.3, 66.5), (3.7, 68.4), (2.9, 70.8), (2.8, 73.6), (3.2, 76.9), (4, 80.7), (5, 85), (-4.5, 86.7), (-6.8, 85.5), (-9.3, 84.8), (-12, 84.5), (-14.6, 84.8), (-17.1, 85.5), (-19.5, 86.7), (-29, 85), (-27.9, 80.7)])
source_poly = Polygon([(25.0, 0.0), (47.5, 0.0), (50.0, 0.0), (50.0, 22.5), (46.9, 23.299999999999997), (44.7, 24.89999999999999), (43.3, 27.0), (42.5, 29.799999999999983), (42.1, 33.19999999999999), (42.0, 37.099999999999994), (42.0, 41.599999999999994), (42.0, 41.900000000000006), (42.0, 42.19999999999999), (42.0, 42.5), (32.5, 44.19999999999999), (30.8, 41.5), (28.1, 39.69999999999999), (25.0, 39.099999999999994), (21.9, 39.69999999999999), (19.2, 41.5), (17.5, 44.19999999999999), (8.0, 42.5), (8.0, 42.19999999999999), (8.0, 41.900000000000006), (8.0, 41.599999999999994), (8.0, 37.099999999999994), (7.899999999999999, 33.19999999999999), (7.5, 29.799999999999983), (6.699999999999999, 27.0), (5.300000000000001, 24.89999999999999), (3.1000000000000014, 23.299999999999997), (0.0, 22.5), (0.0, 0.0), (2.5, 0.0), (25.0, 0.0)])
source_poly_coords = list(source_poly.exterior.coords)
print(source_poly_coords)
translated_list = [(x, y+9.3) for x,y in source_poly_coords]
source_poly_2 = Polygon(translated_list)

def plot_polygon(ax, poly, color, label):
    x, y = poly.exterior.xy
    ax.fill(x, y, alpha=0.5, fc=color, ec='black', label=label)

# Set up the plot
fig, ax = plt.subplots()

# Plot polygons
plot_polygon(ax, target_poly, 'blue', 'target poly')
plot_polygon(ax, source_poly, 'green', 'source poly')
plot_polygon(ax, source_poly_2, 'green', 'source poly 2')

# Plot NFP points
nfp_x, nfp_y = zip(*translation_to_test.coords)
ax.plot(nfp_x, nfp_y, 'ro-', label='translation_to_test')  # red points with lines

# Misc plot settings
ax.set_aspect('equal')
ax.legend()
ax.grid(True)
plt.title("Polygon NFP Visualization")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()
