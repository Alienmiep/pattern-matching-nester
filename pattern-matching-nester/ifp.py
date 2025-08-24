from models.piece import Piece

# input_points = [(14.2, 147.0), (14.2, 154.0), (0.0, 154.0), (-14.2, 154.0), (-14.2, 147.0), (0.0, 147.0)]
input_points_local = [(180.1, 147.0), (170.3, 147.0), (160.5, 147.0), (160.5, 154.0), (170.3, 154.0), (180.1, 154.0)]

reference_point_local = input_points_local[0]

fabric_length = 200  # = x
fabric_width = 150   # = y

fabric_vertices = [(0, 0), (200, 0), (200, 150), (0, 150)]

def ifp(piece: Piece, fabric_vertices: list) -> list:
    input_points = piece.vertices
    # reference_point = min(input_points, key=lambda v: (v[0], v[1]))

    # Transpose the list of tuples to separate x and y values
    x_vals, y_vals = zip(*input_points)

    min_x = min(x_vals)
    min_y = min(y_vals)
    max_x = max(x_vals)
    max_y = max(y_vals)  # to make axis-aligned bounding box of the piece

    ifp_min_x = piece.reference_point[0] - min_x
    ifp_max_x = fabric_length - (max_x - piece.reference_point[0])
    ifp_min_y = piece.reference_point[1] - min_y
    ifp_max_y = fabric_width - (max_y - piece.reference_point[1])
    print(ifp_min_x, ifp_max_x)

    ifp = [(ifp_min_x, ifp_min_y), (ifp_max_x, ifp_min_y), (ifp_max_x, ifp_max_y), (ifp_min_x, ifp_max_y)]
    return ifp

if __name__ == '__main__':
    ifp_vertices = ifp(input_points_local, fabric_vertices)
    ifp_vertices_sorted_by_appeal = list(sorted(ifp_vertices))  # built-in sort does x ascending, then y ascending, so leftest lowest point
    print(ifp_vertices_sorted_by_appeal)

    target_point = ifp_vertices_sorted_by_appeal[0]
    translation = (target_point[0] - reference_point_local[0], target_point[1] - reference_point_local[1])
    print(translation)

    translated_input_points = [(x[0] + translation[0], x[1] + translation[1]) for x in input_points_local]
    print(translated_input_points)
