import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point
from shapely import set_precision, line_merge
from helper import precision_aware_intersection, INTERSECTION_PRECISION
import matplotlib
matplotlib.use('Qt5Agg')


a_poly = Polygon([(0.4, 7.6), (0.6, -0.0), (25.6, -0.0), (25.5, 5.1), (25.4, 10.1), (25.4, 14.8), (25.5, 19.3), (25.5, 23.7), (25.7, 27.8), (25.8, 31.7), (26.0, 35.5), (26.3, 39.0), (26.6, 42.3), (27.0, 45.4), (27.3, 48.4), (27.8, 51.1), (28.3, 53.6), (28.8, 56.0), (29.4, 58.1), (30.0, 60.0), (30.6, 61.7), (31.4, 63.3), (32.1, 64.6), (30.5, 65.0), (29.0, 65.9), (27.8, 67.2), (26.8, 69.1), (26.0, 71.3), (25.4, 74.0), (25.0, 77.2), (24.8, 80.9), (24.9, 85.0), (25.1, 89.6), (25.6, 94.6), (17.1, 94.6), (15.4, 81.1), (13.8, 94.6), (2.3, 94.6), (1.9, 92.8), (1.6, 90.6), (1.4, 88.2), (1.1, 85.4), (0.9, 82.3), (0.7, 79.0), (0.5, 75.3), (0.4, 71.3), (0.2, 67.1), (0.1, 62.5), (0.1, 57.6), (0.0, 52.4), (0.0, 46.9), (0.0, 41.1), (0.0, 35.0), (0.1,28.6), (0.2, 21.9), (0.3, 14.9), (0.4, 7.6)])
b_poly = Polygon([(28.89, 56.32), (28.49, 54.52), (28.19, 52.32), (27.99, 49.92), (27.69, 47.12), (27.49, 44.02), (27.29, 40.72), (27.09, 37.02), (26.89, 33.02), (26.79, 28.82), (26.69, 24.22), (26.69, 19.32), (26.59, 14.12), (26.59, 8.62), (26.59, 2.82), (26.59, -3.28), (26.69, -9.68), (26.79, -16.38), (26.89, -23.38), (26.99, -30.68), (27.19, -38.28), (52.19, -38.28), (52.09, -33.18), (51.99, -28.18), (51.99, -23.48), (52.09, -18.98), (52.09, -14.58), (52.29, -10.48), (52.39, -6.58), (52.59, -2.78), (52.89, 0.72), (53.19, 4.02), (53.49, 7.12), (53.89, 10.12), (54.39, 12.82), (54.89, 15.32), (55.39, 17.72), (55.99, 19.82), (56.59, 21.72), (57.19, 23.42), (57.89, 25.02), (58.69, 26.32), (57.09, 26.72), (55.59, 27.62), (54.39, 28.92), (53.39, 30.82), (52.59, 33.02), (51.99, 35.72), (51.59, 38.92), (51.39, 42.62), (51.49, 46.72), (51.69, 51.32), (52.19, 56.32), (43.69, 56.32), (41.99, 42.82), (40.39, 56.32), (28.89, 56.32)])

print("raw intersection: ", a_poly.intersection(b_poly))

intersection = precision_aware_intersection(a_poly, b_poly)
print("precision-aware intersection: ", intersection)


shared_points = []
linestring_intersection_length = 0
if intersection.geom_type in ["LineString", "MultiLineString"]:
    if intersection.length < 1.1 * INTERSECTION_PRECISION:
        shared_points.append(Point(intersection.coords[0]))

    line_intersection_flag = True
    merged_linestring = line_merge(intersection)
    print(merged_linestring)

    if merged_linestring.geom_type == "LineString":
        shared_points.append(Point(merged_linestring.coords[0]))
        shared_points.append(Point(merged_linestring.coords[-1]))
        linestring_intersection_length = merged_linestring.length

    elif merged_linestring.geom_type == "MultiLineString":
        for line in merged_linestring.geoms:
            linestring_intersection_length += line.length
            if line.length < 2.1 * INTERSECTION_PRECISION:
                shared_points.append(Point(line.coords[0]))
            else:
                shared_points.append(Point(line.coords[0]))
                shared_points.append(Point(line.coords[-1]))

print(shared_points, linestring_intersection_length)


def plot_polygon(ax, poly, color, label):
    x, y = poly.exterior.xy
    ax.fill(x, y, alpha=0.5, fc=color, ec='black', label=label)
    ax.scatter(x, y, color='black', s=10, zorder=5)

# Set up the plot
fig, ax = plt.subplots()

# Plot polygons
plot_polygon(ax, a_poly, 'blue', 'a poly')
plot_polygon(ax, b_poly, 'green', 'b poly')


# Misc plot settings
ax.set_aspect('equal')
ax.legend()
ax.grid(True)
plt.title("Polygon NFP Visualization")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()
