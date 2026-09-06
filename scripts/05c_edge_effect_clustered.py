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
X=[];Y=[];Q=[]
for fp in fs:
    qid,gid,_=os.path.basename(fp)[:-5].rsplit("__",2)
    S=np.asarray(json.load(open(fp))["spins_history"],dtype=int)
    y=gt[qid]; J=JM[gid]
    Jp=(J>0).astype(float); Jn=(J<0).astype(float)
    for t in range(8):
        s=S[t]; nxt=S[t+1]
        cor=(s==y).astype(float); wro=(s==-y).astype(float)
        a=cor@Jp; b=wro@Jp; c=cor@Jn; e=wro@Jn
        z=(s==y).astype(float)
        ok=(nxt!=0)
        X.append(np.column_stack([np.ones(32),z,a,b,c,e])[ok]); Y.append((nxt==y).astype(float)[ok])
        Q.extend([qid]*int(ok.sum()))
X=np.vstack(X); Y=np.concatenate(Y); Q=np.array(Q)
w=np.zeros(X.shape[1])
for _ in range(60):
    p=1/(1+np.exp(-np.clip(X@w,-30,30))); W=np.clip(p*(1-p),1e-8,None)
    g=X.T@(Y-p); H=(X*W[:,None]).T@X + 1e-6*np.eye(X.shape[1])
    w=w+np.linalg.solve(H,g)
p=1/(1+np.exp(-np.clip(X@w,-30,30))); W=np.clip(p*(1-p),1e-8,None)
B=np.linalg.inv((X*W[:,None]).T@X)
r=Y-p
meat=np.zeros((X.shape[1],X.shape[1]))
qs=np.unique(Q)
for q in qs:
    m=Q==q
    gq=X[m].T@r[m]
    meat+=np.outer(gq,gq)
V=B@meat@B
se=np.sqrt(np.diag(V))
nm=["c0","theta","c_T+","c_F+","c_T-","c_F-"]
print(f"## {mc}  n_obs={len(Y)}  n_clusters(qid)={len(qs)}")
for n,v,s0 in zip(nm,w,se): print(f"   {n:6s} {v:+.4f}  (clustered SE {s0:.4f})")
# delta method for w_T = -w2/w3
d=np.zeros(6); d[2]=-1/w[3]; d[3]=w[2]/w[3]**2
vw=d@V@d; sew=np.sqrt(vw)
wt=-w[2]/w[3]
print(f"   w_T = {wt:.3f} +- {1.96*sew:.3f}  (95% CI [{wt-1.96*sew:.3f},{wt+1.96*sew:.3f}])")
# lambda = w4/w2
d2=np.zeros(6); d2[4]=1/w[2]; d2[2]=-w[4]/w[2]**2
sel=np.sqrt(d2@V@d2)
print(f"   lambda = {w[4]/w[2]:.3f} +- {1.96*sel:.3f}")
