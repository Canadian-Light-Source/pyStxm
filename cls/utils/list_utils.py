from functools import reduce


def sum_lst(lst):
    return reduce((lambda x, y: x + y), lst)


def prod_lst(lst):
    return reduce((lambda x, y: x * y), lst)


def merge_to_one_list(lists):
    res_lst = []
    for l in lists:
        for item in l:
            res_lst.append(item)

    return res_lst


def merge_two_to_one(lista, listb):
    rc = [response for ab in zip(lista, listb) for response in ab]
    return rc


def sort_str_list(lst):
    """take a list of strings that may contain integers and sort"""
    # lst.sort(key=lambda f: int(list(filter(str.isdigit, f))))
    lst.sort(key=lambda x: int("".join(filter(str.isdigit, x))))
    return lst

def remove_items(lst, item):
    # using list comprehension to perform the task
    res = [i for i in lst if i != item]
    return res
