

def parse_datarecorder_file(filename):
    """
    open a datarecorder file name and return a dict that contains all curves and data points
    """
    # Variables to store header information and data
    header = {}
    data = []

    # Read the file
    with open(filename, "r") as file:
        # Read header lines until the END_HEADER line
        line = file.readline().strip()
        while line.find("# END_HEADER") == -1:
            if line.find("=") == -1:
                line = file.readline().strip()
                continue
            key, value = line.split("=")
            header[key.strip("# ")] = value.strip()
            line = file.readline().strip()


        # Read data lines
        for line in file:
            values = line.strip().split("\t")
            data.append([float(value) for value in values])

    dct = {}
    dct['header'] = header
    # Extract header information
    type_value = int(header["TYPE"])
    separator_value = int(header["SEPARATOR"])
    dim_value = int(header["DIM"])
    sample_time_value = float(header["SAMPLE_TIME"])
    ndata_value = int(header["NDATA"])

    idxs = list(range(int(ndata_value)))
    time = [t * sample_time_value for t in idxs]
    dct["time"] = time
    dct["data"] = {}
    for i in range(dim_value):
        # Extract data columns
        nm = header[f"NAME{i}"]
        dct["data"][nm] = {}
        if nm.find("Value of Digital Output1") > -1:
            dct["data"][nm] = [int(row[i]) & 2 for row in data[:ndata_value]]
        else:
            dct["data"][nm] = [row[i] for row in data[:ndata_value]]

    return(dct)