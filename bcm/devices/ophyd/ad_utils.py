

def gen_list_of_row_change_img_indexs(npoints_per_row, num_rows, first_img_idx=0, num_extra_trigs_per_row=1,subdir="/00_00",fprefix="FPREFIX",fsuffix="h5"):
    """
    C230728003_000030.h5
    generate a list of image index numbers that represent the images that would have been
    acquired when the scan was changing to next row, those images will be removed at teh end of the
    scan because they are essentially garbage
    Typically
    num_extra_trigs_per_row = 1

    """
    rmv_img_idx_lst = []
    idx = first_img_idx
    while idx < first_img_idx + (npoints_per_row * num_rows):
        #make npoints_per_row zero based
        if idx == first_img_idx:
            idx += npoints_per_row
            rmv_img_idx_lst.append(idx)
        else:
            idx += npoints_per_row + num_extra_trigs_per_row
            rmv_img_idx_lst.append(idx)
    idx += 1
    #add the extra files produced by the extra row from E712 for triggering SIS3820
    rmv_img_idx_lst.extend(list(range(idx, idx + npoints_per_row + num_extra_trigs_per_row + num_extra_trigs_per_row)))
    fnames_lst = []
    for r_idx in rmv_img_idx_lst:
        fs = f"{subdir}/{fprefix}_{r_idx:06d}.{fsuffix}"
        fnames_lst.append(fs)

    return rmv_img_idx_lst, fnames_lst

def gen_list_of_outter_inner_row_change_img_indexs(num_outer_inner, npoints_per_row, num_rows, first_img_idx=0, num_extra_trigs_per_row=1,subdir="/00_00",fprefix="FPREFIX",fsuffix="h5"):
    """
    generate a list of image index numbers that represent the images that would have been
    acquired when the scan was changing to next row, those images will be removed at teh end of the
    scan because they are essentially garbage
    Typically
    num_extra_trigs_per_row = 1

    """
    main_remove_dct = {}
    main_rmv_img_idx_lst = []
    first_img_idx = 0
    for xx in range(num_outer_inner):
        r_idx_lst, r_fnames = gen_list_of_row_change_img_indexs(npoints_per_row, num_rows,first_img_idx=first_img_idx,subdir=f"/{xx:02d}_00",fprefix=fprefix,fsuffix=fsuffix)
        #main_rmv_img_idx_lst.append(gen_list_of_row_change_img_indexs(npoints_per_row, num_rows,first_img_idx=first_img_idx))
        main_remove_dct[xx] = {"r_idxs": r_idx_lst, "r_fnames": r_fnames}
        first_img_idx += (npoints_per_row + num_extra_trigs_per_row) * num_rows
    return main_remove_dct



if __name__ == '__main__':
    num_outter = 5
    num_inner = 2
    # C230728003_000037
    #this will be called at the start of every inner iterations and so the subdir will be known and passed in
    # rmv_lst = gen_list_of_outter_inner_row_change_img_indexs((num_outter + num_inner), 5, 5,subdir="/00_00/",fprefix="C230728003",fsuffix="h5")
    # for k,v in rmv_lst.items():
    #     print(k,v)

    r_idx_lst, r_fnames = gen_list_of_row_change_img_indexs(5, 5, first_img_idx=0, subdir=f"/00_00", fprefix="C230728003",fsuffix="h5")
    for f in r_fnames:
        print(f)