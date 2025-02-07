
import hashlib
import base64

def gen_unique_id_from_string(s):
    d = hashlib.md5(bytes(s.encode('utf-8'))).digest()
    h = bytes([
        d[0] ^ d[1] ^ d[2] ^ d[3] ^ d[14] ^ d[15],
        d[4] ^ d[5] ^ d[6] ^ d[7] ^ d[13],
        d[8] ^ d[9] ^ d[10] ^ d[11] ^ d[12]],
    )
    id_str = base64.urlsafe_b64encode(h).decode('utf-8')
    return(id_str)

