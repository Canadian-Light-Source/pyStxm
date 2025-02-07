
from cls.utils.scan_estimation.estimator import EstimateScanTimeClass, run_estimations


# # Example data (list of tuples)
#detector data
data = [
    # (5, 5, 5, 1),  # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
    # (5, 5, 5, 10),
    # (8, 5, 5, 100),
    # (36, 15, 15, 1),
    # (37, 15, 15, 10),
    # (59, 15, 15, 100),
    # (60, 30, 30, 1),
    # (71, 30, 30, 10),
    # (154, 30, 30, 100),
    # (124, 40, 40, 10),
    # (201, 50, 50, 10),
    # (300, 50, 50, 50),
    # (420, 50, 50, 100),
    (250, 50, 50, 100),
]

#stack image data
data = [[164.0, 150, 150, 1.0, 4, 1], [160.0, 150, 150, 1.0, 4, 1], [164.0, 150, 150, 1.0, 4, 1], [160.0, 150, 150, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [40.0, 150, 150, 1.0, 1, 1], [41.0, 150, 150, 1.0, 1, 1], [40.0, 150, 150, 1.0, 1, 1], [41.0, 150, 150, 1.0, 1, 1]]
data = [[82.22092390060425, 150, 150, 1.0, 2, 1], [115.28390741348267, 100, 100, 1.0, 5, 1], [207.27106189727783, 150, 150, 1.0, 5, 1], [30.998793601989746, 150, 150, 1.0, 3, 1], [18.01468586921692, 50, 50, 1.0, 2, 1], [125.13001370429993, 300, 300, 1.0, 1, 1], [255.1, 300, 300, 1.0, 2, 1], [625.1, 300, 300, 1.0, 5, 1]]
#model_fpath = "c:/test_data/stxm/det_scan_model.pkl"
#model = load_model(model_fpath)

# # Example usage
# for d in data:
#     actual = d[0]
#     test_points_x = d[1]
#     test_points_y = d[2]
#     test_dwell_time = d[3]
#     test_numev = d[4]
#     test_numpol = d[5]

estc = EstimateScanTimeClass(degree=3, alpha=0.1)

actual, estimated = run_estimations(estc, 'sample_image_stack', data)

# # now test updating the model following the execution of a scan
# # generic scan ('generic_scan', [80.0, 150, 1, 200.0])
# estc.add_data_to_scan('sample_image_stack', [140.0, 150, 150, 1.0, 3, 1])
#
# # check that the generic scan is more accurate in estimating
# actual, estimated = run_estimations(estc, 'sample_image_stack', data)

