input_points = [(14.2, 147.0), (14.2, 154.0), (0.0, 154.0), (-14.2, 154.0), (-14.2, 147.0), (0.0, 147.0)]

reference_point = input_points[0]

fabric_length = 200  # = x
fabric_width = 150   # = y

fabric_vertices = [(0, 0), (200, 0), (200, 150), (0, 150)]

# Transpose the list of tuples to separate x and y values
x_vals, y_vals = zip(*input_points)

min_x = min(x_vals)
min_y = min(y_vals)
max_x = max(x_vals)
max_y = max(y_vals)  # to make axis-aligned bounding box of the piece

ifp_min_x = reference_point[0] - min_x
ifp_max_x = fabric_length - (max_x - reference_point[0])
ifp_min_y = reference_point[1] - min_y
ifp_max_y = fabric_width - (max_y - reference_point[1])

ifp = [(ifp_min_x, ifp_min_y), (ifp_max_x, ifp_min_y), (ifp_max_x, ifp_max_y), (ifp_min_x, ifp_max_y)]

ifp_vertices_sorted_by_appeal = list(sorted(ifp))  # built-in sort does x ascending, then y ascending, so leftest lowest point
print(ifp_vertices_sorted_by_appeal)

target_point = ifp_vertices_sorted_by_appeal[0]
translation = (target_point[0] - reference_point[0], target_point[1] - reference_point[1])
print(translation)

translated_input_points = [(x[0] + translation[0], x[1] + translation[1]) for x in input_points]
print(translated_input_points)
