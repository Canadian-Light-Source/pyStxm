from cls.utils.scan_estimation.estimator import *

if __name__ == '__main__':

    # Example data (list of tuples)
    detector_scan_data = [
        (5, 5, 5, 1),  # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
        (5, 5, 5, 10),
        (8, 5, 5, 100),
        (36, 15, 15, 1),
        (37, 15, 15, 10),
        (59, 15, 15, 100),
        (60, 30, 30, 1),
        (71, 30, 30, 10),
        (154, 30, 30, 100),
        (124, 40, 40, 10),
        (201, 50, 50, 10),
        (300, 50, 50, 50),
        (420, 50, 50, 100),
    ]

    scan_name = 'coarse_image'
    coarse_image_data = [[96.0, 200, 50, 5.0], [107.0, 200, 50, 5.0], [300.0, 100, 100, 10.0], [260.0, 100, 100, 10.0], [5.0, 100, 100, 10.0], [17.0, 100, 100, 10.0], [25.0, 100, 100, 10.0], [156.0, 100, 100, 10.0], [61.0, 100, 100, 10.0], [70.0, 100, 100, 10.0], [100.0, 100, 100, 10.0], [180.0, 100, 100, 10.0], [88.0, 100, 100, 10.0], [133.0, 100, 100, 4.0], [148.0, 100, 100, 4.0], [98.0, 220, 50, 2.0], [133.0, 100, 100, 2.5], [118.0, 100, 100, 2.5], [126.0, 100, 100, 2.5], [19.0, 100, 100, 2.5], [3.0, 100, 100, 2.5], [85.0, 100, 100, 2.5], [119.0, 100, 100, 2.5], [49.0, 100, 30, 10.0], [83.0, 100, 30, 10.0], [147.0, 100, 100, 4.5], [105.0, 100, 100, 2.0], [110.0, 100, 100, 2.0], [106.0, 100, 100, 2.0], [107.0, 100, 100, 2.0], [53.0, 100, 100, 2.0], [109.0, 100, 100, 2.0], [268.0, 100, 100, 2.0], [119.0, 100, 100, 2.0], [90.0, 100, 100, 5.0], [26.0, 100, 100, 5.0], [70.0, 100, 100, 5.0], [272.0, 100, 100, 5.0], [182.0, 100, 100, 5.0], [148.0, 100, 100, 5.0], [181.0, 100, 100, 5.0], [142.0, 100, 100, 5.0], [16.0, 100, 100, 5.0], [187.0, 100, 100, 5.0], [326.0, 100, 100, 5.0], [50.0, 100, 100, 5.0], [33.0, 100, 100, 5.0], [186.0, 100, 100, 5.0], [153.0, 100, 100, 5.0], [162.0, 100, 100, 5.0], [144.0, 100, 100, 5.0], [153.0, 100, 100, 5.0], [162.0, 100, 100, 5.0], [181.0, 100, 100, 5.0], [142.0, 100, 100, 5.0], [58.0, 100, 100, 5.0], [123.0, 100, 100, 5.0], [105.0, 100, 100, 5.0], [15.0, 150, 50, 2.0], [11.0, 150, 50, 2.0], [8.0, 150, 50, 2.0], [69.0, 150, 50, 2.0], [129.0, 150, 50, 2.0], [67.0, 150, 50, 2.0], [68.0, 150, 50, 2.0], [73.0, 150, 50, 2.0], [76.0, 150, 50, 2.0], [68.0, 150, 50, 2.0], [11.0, 150, 50, 2.0], [15.0, 150, 50, 2.0], [12.0, 150, 50, 2.0], [17.0, 150, 50, 2.0], [13.0, 150, 50, 2.0], [8.0, 150, 50, 2.0], [14.0, 150, 50, 2.0], [9.0, 150, 50, 2.0], [9.0, 150, 50, 2.0], [16.0, 150, 50, 2.0], [77.0, 150, 50, 2.0], [64.0, 150, 50, 2.0], [16.0, 150, 50, 2.0], [23.0, 150, 50, 2.0], [8.0, 150, 50, 2.0], [13.0, 150, 50, 2.0], [25.0, 150, 50, 2.0], [26.0, 150, 50, 2.0], [24.0, 150, 50, 2.0], [28.0, 150, 50, 2.0], [66.0, 150, 50, 2.0], [14.0, 150, 50, 2.0], [15.0, 150, 50, 2.0], [19.0, 150, 50, 2.0], [77.0, 150, 50, 2.0], [114.0, 150, 50, 2.0], [91.0, 150, 50, 2.0], [76.0, 150, 50, 2.0], [66.0, 150, 50, 2.0], [72.0, 150, 50, 2.0], [69.0, 150, 50, 2.0], [55.0, 150, 50, 2.0], [34.0, 150, 50, 2.0], [15.0, 150, 50, 2.0], [74.0, 150, 50, 2.0], [9.0, 150, 50, 2.0], [45.0, 150, 50, 2.0], [16.0, 150, 50, 2.0], [20.0, 150, 50, 2.0], [67.0, 150, 50, 2.0], [66.0, 150, 50, 2.0], [181.0, 150, 50, 2.0], [79.0, 150, 50, 2.0], [49.0, 150, 50, 2.0], [75.0, 150, 50, 2.0], [65.0, 150, 50, 2.0], [74.0, 150, 50, 2.0], [4.0, 150, 50, 2.0], [53.0, 150, 50, 2.0], [44.0, 150, 50, 2.0], [5.0, 150, 50, 2.0], [59.0, 150, 50, 2.0], [60.0, 150, 50, 2.0], [2.0, 150, 50, 2.0], [33.0, 150, 50, 2.0], [73.0, 150, 50, 2.0], [233.0, 150, 150, 2.0], [9.0, 100, 100, 16.0], [10.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [8.0, 100, 50, 5.0], [61.0, 100, 50, 5.0], [82.0, 100, 50, 5.0], [28.0, 100, 50, 5.0], [21.0, 100, 50, 5.0], [98.0, 100, 50, 5.0], [76.0, 100, 50, 5.0], [13.0, 100, 50, 5.0], [106.0, 100, 50, 5.0], [6.0, 100, 50, 5.0], [63.0, 100, 50, 5.0], [114.0, 100, 50, 5.0], [68.0, 100, 50, 5.0], [7.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [35.0, 100, 50, 5.0], [32.0, 100, 50, 5.0], [30.0, 100, 50, 5.0], [31.0, 100, 50, 5.0], [23.0, 100, 50, 5.0], [89.0, 100, 50, 5.0], [34.0, 100, 50, 5.0], [95.0, 100, 50, 5.0], [49.0, 100, 50, 5.0], [21.0, 100, 50, 5.0], [95.0, 100, 50, 5.0], [76.0, 100, 50, 5.0], [48.0, 100, 50, 5.0], [76.0, 100, 50, 5.0], [92.0, 100, 50, 5.0], [93.0, 100, 50, 5.0], [68.0, 100, 50, 5.0], [66.0, 100, 50, 5.0], [58.0, 100, 50, 5.0], [92.0, 100, 50, 5.0], [74.0, 100, 50, 5.0], [33.0, 100, 50, 5.0], [28.0, 100, 50, 5.0], [60.0, 100, 50, 5.0], [88.0, 100, 50, 5.0], [90.0, 100, 50, 5.0], [93.0, 100, 50, 5.0], [75.0, 100, 50, 5.0], [73.0, 100, 50, 5.0], [9.0, 100, 50, 5.0], [100.0, 100, 50, 5.0], [9.0, 100, 50, 5.0], [29.0, 100, 50, 5.0], [14.0, 100, 50, 5.0], [97.0, 100, 50, 5.0], [43.0, 100, 50, 5.0], [39.0, 100, 50, 5.0], [85.0, 100, 50, 5.0], [65.0, 100, 50, 5.0], [69.0, 100, 50, 5.0], [60.0, 100, 50, 5.0], [28.0, 100, 50, 5.0], [7.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [36.0, 100, 50, 5.0], [13.0, 100, 50, 5.0], [82.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [74.0, 100, 50, 5.0], [114.0, 100, 50, 5.0], [95.0, 100, 50, 5.0], [82.0, 100, 50, 5.0], [70.0, 100, 50, 5.0], [80.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [48.0, 100, 50, 5.0], [65.0, 100, 50, 5.0], [29.0, 100, 50, 5.0], [84.0, 100, 50, 5.0], [9.0, 100, 50, 5.0], [81.0, 100, 50, 5.0], [41.0, 100, 50, 5.0], [115.0, 100, 50, 5.0], [59.0, 100, 50, 5.0], [90.0, 100, 50, 5.0], [33.0, 100, 50, 5.0], [66.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [65.0, 100, 50, 5.0], [6.0, 100, 50, 5.0], [80.0, 100, 50, 5.0], [58.0, 100, 50, 5.0], [67.0, 100, 50, 5.0], [78.0, 100, 50, 5.0], [54.0, 100, 50, 5.0], [54.0, 100, 50, 5.0], [75.0, 100, 50, 5.0], [39.0, 100, 50, 5.0], [62.0, 100, 50, 5.0], [26.0, 100, 50, 5.0], [21.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [87.0, 100, 50, 5.0], [14.0, 100, 50, 5.0], [19.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [86.0, 100, 50, 5.0], [20.0, 100, 50, 5.0], [31.0, 100, 50, 5.0], [46.0, 100, 50, 10.0], [12.0, 100, 50, 10.0], [133.0, 100, 50, 10.0], [128.0, 100, 50, 10.0], [56.0, 100, 50, 10.0], [46.0, 100, 50, 10.0], [74.0, 100, 50, 10.0], [25.0, 100, 50, 10.0], [125.0, 100, 50, 10.0], [114.0, 100, 50, 10.0], [115.0, 100, 50, 10.0], [128.0, 100, 50, 10.0], [23.0, 100, 50, 10.0], [43.0, 100, 50, 10.0], [35.0, 100, 50, 10.0], [123.0, 100, 50, 10.0], [98.0, 100, 50, 10.0], [106.0, 100, 50, 10.0], [128.0, 100, 50, 10.0], [28.0, 100, 50, 10.0], [82.0, 100, 50, 10.0], [86.0, 100, 50, 10.0], [114.0, 100, 50, 10.0], [100.0, 100, 50, 10.0], [25.0, 100, 50, 10.0], [25.0, 100, 50, 10.0], [44.0, 100, 50, 10.0], [44.0, 100, 50, 10.0], [76.0, 100, 50, 10.0], [129.0, 100, 50, 10.0], [127.0, 100, 50, 10.0], [60.0, 100, 50, 10.0], [117.0, 100, 50, 10.0], [79.0, 100, 50, 10.0], [18.0, 100, 50, 10.0], [81.0, 100, 50, 10.0], [126.0, 100, 50, 10.0], [126.0, 100, 50, 10.0], [27.0, 100, 50, 10.0], [12.0, 100, 50, 10.0], [39.0, 100, 50, 10.0], [99.0, 100, 50, 10.0], [37.0, 100, 50, 10.0], [105.0, 100, 50, 10.0], [66.0, 100, 50, 10.0], [108.0, 100, 50, 10.0], [117.0, 100, 50, 10.0], [100.0, 100, 50, 10.0], [89.0, 100, 50, 10.0], [54.0, 100, 50, 10.0], [107.0, 100, 50, 10.0], [40.0, 100, 30, 2.5], [18.0, 75, 75, 2.0], [67.0, 100, 30, 5.0]]
    scan_data = coarse_image_data
    # # Example usage
    test_points_x = 10
    test_points_y = 10
    test_dwell_time = 100.0
    estc = EstimateScanTimeClass()
    #estc.build_data_from_datafiles()
    print(f"\nTesting [{scan_name}]")

    # # Example usage
    test_points_x = 100
    test_points_y = 100
    test_dwell_time = 2.5
    # actual is 88 seconds for coarse_image

    for sd in scan_data:
        estc.add_scan(scan_name, data=sd)
        print(f"\t{test_points_x} x {test_points_y} x {test_dwell_time} ms ")
        #print(f"\t actual={sd[0]} ms,    estimated={estc.estimate_scan_time(scan_name, test_points_x, test_points_y, test_dwell_time)} ms")
        print(
            f"\t estimated={estc.estimate_scan_time(scan_name, test_points_x, test_points_y, test_dwell_time)} ms")
    #model_fpath = "c:/test_data/stxm/det_scan_model.pkl"
    #fit_model(detector_scan_data, model_fpath)
    #model = load_model(model_fpath)
    #estimate_scan_time(model, test_points_x, test_points_y, test_dwell_time)
