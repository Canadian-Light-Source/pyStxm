import zmq
import simplejson as json

def gen_tiled_map(image_width, image_height, block_width, block_height):
    block_coordinates = {}
    block_num = 0

    # Loop through the grid, block by block
    for y in range(0, image_height, block_height):
        for x in range(0, image_width, block_width):
            # For each block, record the starting x, y coordinates
            block_coordinates[block_num] = (y, x)
            block_num += 1

    return block_coordinates
def gen_non_tiled_map(num_blocks, arr_npoints, npoints_x):
    dct = {}
    for block_idx in range(num_blocks):
        dct[block_idx] = gen_non_tiled_map_entry(block_idx, arr_npoints, npoints_x)
    return dct

def gen_non_tiled_map_entry(sdInnerRegionIdx, arr_npoints, npoints_x):
    # npoints_x = Number of pixels each data array represents
    # Calculate the starting pixel index in the 1D image representation
    starting_pixel_index = sdInnerRegionIdx * arr_npoints

    # Calculate the grid locations for all 20 points
    #pixel_positions = []
    pixel_row = (starting_pixel_index + 0) // npoints_x
    pixel_col = (starting_pixel_index + 0) % npoints_x
    #pixel_positions.append((pixel_row, pixel_col))

    # dct = {}
    # dct[sdInnerRegionIdx] = {'row': pixel_positions[0][0], 'col': pixel_positions[0][1]}
    return {'row': pixel_row, 'col': pixel_col}

def pub_monitor(host, port, ignore_detector=False):
    # Create a ZeroMQ context
    context = zmq.Context()

    # Create a SUB socket to subscribe to the PUB socket
    sub_socket = context.socket(zmq.SUB)

    # Connect to the PUB socket using the provided host and port
    sub_socket.connect(f"tcp://{host}:{port}")

    # Subscribe to all messages (empty string subscribes to all topics)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')

    print(f"Monitoring PUB socket at tcp://{host}:{port}...")
    j = 0
    num_data_points = 0
    num_ttl_data_points = 0
    is_tiling = False
    col = 0
    prev_block_num = -1
    sdInnerRegionIdx = -1
    nInnerRegions = 0
    nOuterRegions = 0
    npoints_x = 1
    npoints_y = 1
    non_tiled_map = {}
    tiled_map = {}
    tile_blk_ht_npts = 1
    while True:
        try:
            # Receive multipart message
            parts = []
            #print(f"[{j}] WAITING FOR NEXT MESSAGE")
            #message_part = sub_socket.recv_string()
            parts = sub_socket.recv_multipart()
            # Check if this is the last part of the multipart message
            # if not sub_socket.getsockopt(zmq.RCVMORE):
            #     break

            msg_parts = []
            for idx, part in enumerate(parts):
                # dct = json.loads(part.decode('utf-8'))
                #print(f"message_parts={message_parts}")
                #print(f"Part {idx + 1}: {part.decode('utf-8')}")
                msg_parts.append(part.decode('utf-8'))
            if msg_parts[0].find('detectorValues') > -1:
                pass
            elif msg_parts[0].find('scanStarted') > -1:
                scan_request = json.loads(msg_parts[1])
                is_tiling = True if scan_request["tiling"] == 1 else False
                nInnerRegions = scan_request['nInnerRegions']
                nOuterRegions = scan_request['nOuterRegions']

                #for now assume 1 inner and outer region
                npoints_x = scan_request['innerRegions'][0]['axes'][0]['nPoints']
                npoints_y = scan_request['innerRegions'][0]['axes'][1]['nPoints']

            elif msg_parts[0].find('scanFinished') > -1 or msg_parts[0].find('scanAborted') > -1:
                is_tiling = False
                j = 0
                num_data_points = 0
                num_ttl_data_points = 0
                col = 0
                prev_block_num = -1
                sdInnerRegionIdx = -1
                non_tiled_map = {}
                tiled_map = {}
                tile_blk_ht_npts = 1

            elif msg_parts[0].find('scanLineData') > -1:
                for i, part in enumerate(msg_parts, start=0):
                    if i == 1:
                        # print(f"  Part {i}: {part}")
                        parts = part.split()
                        sdPolarizationIdx = int(parts[0])
                        sdOuterRegionIdx = int(parts[1])
                        sdInnerRegionIdx = block_num = int(parts[2])
                        channelIdx = int(parts[3])
                        print(f"\tsdPolarizationIdx={parts[0]}, sdOuterRegionIdx={parts[1]}, sdInnerRegionIdx={parts[2]}, det channelIdx={parts[3]}")
                    elif i == 2:
                        parts = part.split()
                        start_idx0 = int(parts[0])
                        start_idx1 = int(parts[1])
                        #col = int(parts[1])
                        print(f"\tstartIdx: [{parts[0]},{parts[1]}]")
                    elif i == 3:
                        parts = part.split()
                        # print(f"  Part {i}: {part}")
                        data_shape = int(parts[0]), int(parts[1])
                        data_npoints = data_shape[1]
                        num_ttl_data_points += data_shape[1]
                        print(f"\tdatashape=[{parts[0]},{parts[1]}]")
                    elif i == 4:
                        # print(f"  Part {i}: {part}")
                        #data = json.loads(part)
                        if is_tiling:
                            # if tiling is on, sdInnerRegionIdx is the current block and startIdx[0] is the block row
                            if len(tiled_map) == 0:
                                tiled_map = gen_tiled_map(npoints_x, npoints_y, data_npoints, data_npoints)
                            # col = sdInnerRegionIdx
                            # row = start_idx0
                            row, col = tiled_map[sdInnerRegionIdx]

                        else:
                            if len(non_tiled_map) == 0:
                                tile_blk_ht_npts = data_npoints
                                #generate the map
                                ttl_num_blocks = int((npoints_x*npoints_y) / data_npoints)
                                non_tiled_map = gen_non_tiled_map(ttl_num_blocks, data_npoints, npoints_x)
                            row = non_tiled_map[sdInnerRegionIdx]['row']
                            col = non_tiled_map[sdInnerRegionIdx]['col']

                        print(f"\tData Array: [{col}, {row+start_idx0}] = {part}")
                        print(f"Total acquired points = {num_ttl_data_points}\n\n")

                        print()

        except zmq.ZMQError as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    # Set the host and port dynamically
    HOST = "VOPI1610-005"  # Replace with the PUB socket host
    PORT = 56561        # Replace with the PUB socket port

    # Start the PUB socket monitor
    pub_monitor(HOST, PORT)
