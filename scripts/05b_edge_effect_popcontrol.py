import json,glob,os,sys,random
import numpy as np
REPO="external/physics-of-agents"
MD={"gpt":"gpt-4o-mini","gma":"gemma-3n-e4b-it","qwn":"qwen3.5-9b","lma":"meta-llama-3-8b-instruct"}
mc=sys.argv[1]; NF=int(sys.argv[2])
gt={}
for sp in ("train","test"):
    for line in open(f"{REPO}/data/obj/{sp}.jsonl"):
        q=json.loads(line); gt[q["qid"]]=1 if q["answer"]=="A" else -1
JM={d['id']:np.array(d['J'],dtype=int) for d in json.load(open(f"{REPO}/data/J_matrices.json"))['graphs']}
fs=[f for f in sorted(glob.glob(f"{REPO}/data/models/{MD[mc]}/objective_energy/*.json")) if not f.endswith("manifest.json")]
fs=[f for f in fs if os.path.basename(f)[:-5].rsplit("__",2)[1] not in ("square","triangular")]
random.Random(0).shuffle(fs); fs=fs[:NF]
X=[];Y=[]
for fp in fs:
    qid,gid,_=os.path.basename(fp)[:-5].rsplit("__",2)
    S=np.asarray(json.load(open(fp))["spins_history"],dtype=int)   # (9,32)
    y=gt[qid]; J=JM[gid]
    Jp=(J>0).astype(float); Jn=(J<0).astype(float)                 # J[i,j]: i->j
    for t in range(8):
        s=S[t]; nxt=S[t+1]
        cor=(s==y).astype(float); wro=(s==-y).astype(float)        # senders
        a=cor@Jp; b=wro@Jp; c=cor@Jn; e=wro@Jn                     # per receiver j
        z=(s==y).astype(float)
        ok=(nxt!=0)
        X.append(np.column_stack([np.ones(32),z,a,b,c,e,np.full(32,cor.mean())])[ok]); Y.append((nxt==y).astype(float)[ok])
X=np.vstack(X); Y=np.concatenate(Y)
w=np.zeros(X.shape[1])
for _ in range(60):
    p=1/(1+np.exp(-np.clip(X@w,-30,30))); W=np.clip(p*(1-p),1e-8,None)
    g=X.T@(Y-p); H=(X*W[:,None]).T@X + 1e-6*np.eye(X.shape[1])
    w=w+np.linalg.solve(H,g)
p_=1/(1+np.exp(-np.clip(X@w,-30,30)))
W_=np.clip(p_*(1-p_),1e-8,None)
se=np.sqrt(np.diag(np.linalg.inv((X*W_[:,None]).T@X)))
nm=["intercept","own_correct(theta)","corr_msg_AGREElabel","wrong_msg_AGREElabel","corr_msg_DISAGREElabel","wrong_msg_DISAGREElabel","pop_x(t) control"]
print(f"## {mc}  n_obs={len(Y)}  n_episodes={len(fs)}")
for n,v,s in zip(nm,w,se): print(f"   {n:26s} {v:+.4f}  (SE {s:.4f})")
print(f"   implied w_T (agree-label)  = {w[2]/-w[3]:.3f}" if w[3]<0 else f"   agree-label wrong-msg coef is POSITIVE ({w[3]:+.3f})")
