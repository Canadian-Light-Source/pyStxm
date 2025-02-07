# def array_position_in_image(n):
#     # Number of pixels each data array represents
#     array_size = 20
#
#     # Calculate the starting pixel index in the 1D image representation
#     starting_pixel_index = n * array_size
#
#     # Convert to row and column in 100x100 grid
#     row = starting_pixel_index // 100
#     col = starting_pixel_index % 100
#
#     # Calculate the grid locations for all 20 points
#     pixel_positions = []
#     # for i in range(array_size):
#     #     pixel_row = (starting_pixel_index + i) // 100
#     #     pixel_col = (starting_pixel_index + i) % 100
#     #     pixel_positions.append((pixel_row, pixel_col))
#     pixel_row = (starting_pixel_index + 0) // 100
#     pixel_col = (starting_pixel_index + 0) % 100
#     pixel_positions.append((pixel_row, pixel_col))
#
#     dct = {}
#     dct[n] = {'row': pixel_positions[0][0], 'col': pixel_positions[0][1]}
#     return (row, col), pixel_positions, dct

def gen_non_tiled_map(sdInnerRegionIdx, npoints_x):
    # npoints_x = Number of pixels each data array represents
    # Calculate the starting pixel index in the 1D image representation
    starting_pixel_index = sdInnerRegionIdx * npoints_x

    # Calculate the grid locations for all 20 points
    pixel_positions = []
    pixel_row = (starting_pixel_index + 0) // 100
    pixel_col = (starting_pixel_index + 0) % 100
    pixel_positions.append((pixel_row, pixel_col))

    dct = {}
    dct[sdInnerRegionIdx] = {'row': pixel_positions[0][0], 'col': pixel_positions[0][1]}
    return dct


n = 50  # Example index of the data array
# Example usage
# for i in range(n):
#     starting_position, pixel_positions, dct = array_position_in_image(i)
#     #for pixel_position in pixel_positions:
#     print(f"for sdInnerRegionIdx = {i}, pixel_positions={pixel_positions[0]}")

for i in range(n):
    starting_position, pixel_positions, dct = array_position_in_image(i)
    #for pixel_position in pixel_positions:
    print(f"dct={dct}")