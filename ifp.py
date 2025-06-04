input_points = [(14.2, 147.0), (14.2, 154.0), (0.0, 154.0), (-14.2, 154.0), (-14.2, 147.0), (0.0, 147.0)]
normalized_input = [(x + 14.2, y) for x, y in input_points]

reference_point = normalized_input[0]

fabric_length = 200  # = x
fabric_width = 150   # = y

fabric_vertices = [(0, 0), (200, 0), (200, 150), (0, 150)]

# Transpose the list of tuples to separate x and y values
x_vals, y_vals = zip(*normalized_input)

min_x = min(x_vals)
min_y = min(y_vals)
max_x = max(x_vals)
max_y = max(y_vals)

print(min_x, min_y, max_x, max_y)
# that's the IFP for rectangular containers, right?
