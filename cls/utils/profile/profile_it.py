import profile
import pstats
import psutil


def determine_profile_bias_val():
    """
    determine_profile_bias_val(): description

    :param determine_profile_bias_val(: determine_profile_bias_val( description
    :type determine_profile_bias_val(: determine_profile_bias_val( type

    :returns: None
    """
    pr = profile.Profile()
    v = 0
    v_t = 0
    for i in range(5):
        v_t = pr.calibrate(100000)
        v += v_t
        print(v_t)

    bval = v / 5.0
    print("bias val = ", bval)
    profile.Profile.bias = bval
    return bval

def profile_it(func, bval=None):
    """
    profile_it(): description

    :param func : the function to profile
    :type bval: bias val

    :returns: None
    """
    if bval == None:
        bval = determine_profile_bias_val()
    else:
        bval = 1.156238437615624e-06

    profile.Profile.bias = bval

    profile.run(f"{func}()", "testprof.dat")

    p = pstats.Stats("testprof.dat")
    p.sort_stats("cumulative").print_stats(100)

if __name__ == '__main__':
    determine_profile_bias_val()