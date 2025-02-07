def convert_plot_poly_to_point_poly(cols, rows, plot_boundaries, poly_positions):
    # Define the plotting positions of the corners
    x_min = plot_boundaries['x_min']
    x_max = plot_boundaries['x_max']
    y_min = plot_boundaries['y_min']
    y_max = plot_boundaries['y_max']

    # Calculate the x and y ranges
    x_range = x_max - x_min
    y_range = y_max - y_min


    # Initialize a list to store the corresponding array indices
    point_indices = []

    # Map each plotting position to its array indices
    for x_plot, y_plot in poly_positions:
        # Calculate the array indices
        col_index = int((x_plot - x_min) / x_range * (cols - 1))
        row_index = int((y_plot - y_min) / y_range * (rows - 1))

        # Append the indices to the list
        point_indices.append((row_index, col_index))

    print("Array indices corresponding to the plotting positions:")
    arr_poly_points = []
    for index in point_indices:
        #print(index)
        arr_poly_points.append(index)

    return arr_poly_points

plot_boundaries = {}
plot_boundaries['x_min'] = -4423.559
plot_boundaries['x_max'] = -4373.559
plot_boundaries['y_min'] = 255.263209216387
plot_boundaries['y_max'] = 305.2632092163869

polygon_lst = [
        (-4410.2620967237435, 300.1748265284598),
        (-4418.095066341328, 291.770042929371),
        (-4411.701980844623, 289.94043017310673),
        (-4405.769658266599, 290.56935955807256),
        (-4402.141150281983, 291.0839381457719)
    ]

rows = 50
cols = 50

pnts = convert_plot_poly_to_point_poly(cols, rows, plot_boundaries, polygon_lst)
print(pnts)