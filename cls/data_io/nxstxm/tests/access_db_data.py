
import os
from databroker import Broker
import cls.data_io.nxstxm as suit_stxm
import time

def dump_docs(docs):
    for d in docs:
        print(d)

def get_headers_from_x_days_ago(db, days_ago):
    #create a new querey called '{days_go}_days_ago', so if user passed 200 days ago the queuery is '200_days_ago'
    db.dynamic_alias('querey', lambda: {'since': time.time() - days_ago * 24 * 60 * 60})
    headers = db.querey
    return headers

def save_headers(db, days_ago=1):
    """
    pull headers from x number of days ago and save them
    """

    i = 0
    headers = list(get_headers_from_x_days_ago(db, days_ago))
    for h in headers:
        try:
            save_header(h, i)
            i += 1
        except:
            pass

def save_header(header, idx=0):
    primary_docs = header.documents(fill=True)

    print(f"Processing: [{idx}]")
    data_dir = "c:/test_data"
    file_prefix = f"new_{idx}"
    first_uid = uid

    if os.path.exists(os.path.join(data_dir, str(uid) + "-new")):
        os.remove(os.path.join(data_dir, str(uid) + "-new"))

    if os.path.exists(os.path.join(data_dir, "new.hdf5")):
        os.remove(os.path.join(data_dir, "new.hdf5"))

    suit_stxm.export(primary_docs, data_dir, file_prefix=file_prefix, first_uid=uid)
    # suit_nxstxm.finish_export(data_dir, fprefix, first_uid, is_stack_dir=is_stack)
    suit_stxm.finish_export(data_dir, file_prefix, first_uid)

if __name__ == '__main__':
    db = Broker.named("pystxm_amb_bl10ID1")
    # uid = 'f9bd0f65-2e9f-4b9b-83a8-400a718a7135'
    # uid = '3684645c-d36f-4402-ad70-95df03316b7b' #detector scan
    uid = '2348a106-d5bf-4d17-9f26-2935f11f6ce8'  # osa focus
    uid = '21ab6b4a-afa0-4f6f-a778-bf19bf00cd0c'  # sample focus
    uid = '34a639f4-0f94-4dc5-b776-d619fbf06707'  # sample focus
    uid = 'f02925c9-8447-4b85-b286-11ff4648648a'  # linespec LxL
    uid = '61a29b59-8379-4884-9085-9049479b4c01'  # linespec PxP
    uid = '44d30cf2-d667-4ac1-8cab-db5c2d0c945f'  # coarse linespec PxP 10x10x3x2
    uid = '012fda02-1d9a-4aac-966e-cec860086d75'  # linespec LxL Fine 40x40x5x10x2
    uid = '50a9a73f-ee9d-4ec5-ba1e-16b3ab0d1661'  # LxL stack
    uid = 'bbb6dd18-8138-4f44-acf2-fba1d5d5301e'  # posner scan
    uid = "8dc36e1f-daf6-41c8-b930-3da88a70f307"  # Focus scan
    uid = "8a63e8a4-b8d7-4b44-a812-0d1eb4e0f368"  # coarse Image
    uid = '836c8fd7-3e25-4ecd-8e5c-72540fe62c9f'  # aborted detector scan
    uid = '1364dd97-9194-4c08-8f62-905de65bb95c'  # coarse failed saving
    # uid = 'a8151920-f59f-4b91-89e3-0e17890040b3' # fails
    uid = '6b52f345-e662-46d6-8ca3-eefad3eca90f'
    uid = '1d2e8bc0-8ac7-47d9-a1a6-b06a208f7334' # point spec data
    uid = '9d19b347-516f-4f51-a2c1-9d6ab6fdc6ea' # aborted stack
    uid = 'b44042e0-2572-4bbb-b770-9772b2d3f3a0'

    # run_uids = ['99350504-05cc-4c8c-8a74-d15cd0f382b0',
    #              'a0daa972-f85b-47f4-9dce-177a10c96951',
    #              '7b52b6d3-3f49-4673-b87b-9369cdb661c8',
    #              '96ba2286-8c6e-41c9-a48a-009e2c3fc53b']
    run_uids = [uid]
    for uid in run_uids:
        header = db[uid]
        save_header(header)
    #save_headers(db, 50)
    # #primary_docs = header.documents(fill=True)
    # #dump_docs(primary_docs)
    # primary_docs = header.documents(fill=True)
    #
    # data_dir = "c:/test_data"
    # file_prefix = "new"
    # first_uid = uid
    #
    # if os.path.exists(os.path.join(data_dir,str(uid) + "-new")):
    #     os.remove(os.path.join(data_dir,str(uid) + "-new"))
    #
    # if os.path.exists(os.path.join(data_dir,"new.hdf5")):
    #     os.remove(os.path.join(data_dir,"new.hdf5"))
    #
    #
    # suit_stxm.export(primary_docs, data_dir, file_prefix=file_prefix, first_uid=uid)
    # # suit_nxstxm.finish_export(data_dir, fprefix, first_uid, is_stack_dir=is_stack)
    # suit_stxm.finish_export(data_dir, file_prefix, first_uid)
