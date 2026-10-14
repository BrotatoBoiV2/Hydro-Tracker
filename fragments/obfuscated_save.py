import os as _o,sys as _s,uuid as _u,base64 as _b,hashlib as _h,subprocess as _p;from argon2.low_level import hash_secret_raw as _hsr,Type as _T;from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _A
_g=lambda m,f:getattr(m,f);_xd=lambda b,k=42:bytes(x^k for x in b).decode('utf-8');_O=[b'\x05O^I\x05GKIBCDO\x07CN',b'\x05\\KX\x05FCH\x05NH_Y\x05GKIBCDO\x07CN',b'lKFFHKIAyOXCKF',b'lKFFHKIAgKIBCDOcn',b'FYHFA',b'\x07D',b'\x07E',b'yoxckf',b'bSNXE~XKIAOXyKF^',b'\x07\x07ODIXSZ^',b'\x07\x07NOIXSZ^']
_mad=lambda:":".join(f"{_u.getnode():012x}"[i:i+2] for i in range(0,12,2));_mid=lambda:next((f.read().strip() for p in[_xd(_O[0]),_xd(_O[1])] if _g(_o,'path').exists(p) for f in[open(p,"r")]),_xd(_O[3]))
_ds=lambda:next((s[0] if s else _xd(_O[2]) for r in[_g(_p,'run')([_xd(_O[4]),_xd(_O[5]),_xd(_O[6]),_xd(_O[7])],stdout=-1,stderr=-1,text=True,check=True)] for s in[[l.strip() for l in r.stdout.split("\n") if l.strip()]]),_xd(_O[2]))
_hf=lambda:_g(_h,'sha256')(f"{_mid()}-{_ds()}-{_mad()}".encode('utf-8')).hexdigest();_dk=lambda r:_hsr(secret=r+_hf().encode('utf-8'),salt=_xd(_O[8]).encode('utf-8'),time_cost=3,memory_cost=65536,parallelism=4,hash_len=32,type=_T.ID)
ep=lambda p:next((_g(_b,'b64encode')(r+n+_A(_dk(r)).encrypt(n,p.encode('utf-8'),None)).decode('utf-8') for r in[_o.urandom(16)] for n in[_o.urandom(12)]));dp=lambda s:next((_A(_dk(b[0:16])).decrypt(b[16:28],b[28:],None).decode('utf-8') for b in[_g(_b,'b64decode')(s.encode('utf-8'))]))
if __name__=="__main__":
 if len(_s.argv)<3:_s.exit(1)
 v,o=_s.argv[1],_s.argv[2];print(ep(v)) if o==_xd(_O[9]) else(print(dp(v)) if o==_xd(_O[10]) else _s.exit(1))
