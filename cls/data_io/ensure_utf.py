import h5py
import os
import numpy as np

def ensure_utf8_in_hdf5(input_filename):
    output_filename = os.path.join(
        os.path.dirname(input_filename),
        "utf-" + os.path.basename(input_filename)
    )
    with h5py.File(input_filename, 'r') as src, h5py.File(output_filename, 'w') as dst:
        def copy_group(src_group, dst_group):
            # Copy attributes
            for key, value in src_group.attrs.items():
                if isinstance(value, bytes):
                    dst_group.attrs[key] = value.decode('utf-8')
                elif isinstance(value, str):
                    dst_group.attrs[key] = value
                else:
                    dst_group.attrs[key] = value
            # Copy datasets and subgroups
            for name, item in src_group.items():
                if isinstance(item, h5py.Dataset):
                    data = item[()]
                    # Handle byte string datasets
                    if item.dtype.kind == 'S':
                        if isinstance(data, bytes):
                            data = data.decode('utf-8')
                        elif isinstance(data, np.ndarray):
                            data = data.astype('U')
                    # Create dataset, let h5py infer dtype if scalar
                    if hasattr(data, 'dtype'):
                        dst_group.create_dataset(name, data=data, dtype=data.dtype)
                    else:
                        dst_group.create_dataset(name, data=data)
                    # Copy dataset attributes
                    for k, v in item.attrs.items():
                        if isinstance(v, bytes):
                            dst_group[name].attrs[k] = v.decode('utf-8')
                        elif isinstance(v, str):
                            dst_group[name].attrs[k] = v
                        else:
                            dst_group[name].attrs[k] = v
                elif isinstance(item, h5py.Group):
                    new_group = dst_group.create_group(name)
                    copy_group(item, new_group)
        copy_group(src, dst)
    print(f"Saved UTF-8 encoded file as: {output_filename}")


if __name__ == "__main__":
    import sys
    # if len(sys.argv) != 2:
    #     print("Usage: python ensure_utf8_in_hdf5.py <input_hdf5_file>")
    #     sys.exit(1)
    # input_file = sys.argv[1]
    input_file = '/home/bergr/srv-unix-home/Data/0502/A240502001.hdf5'
    ensure_utf8_in_hdf5(input_file)