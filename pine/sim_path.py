import random
LEGS=[(-4,0),(2.4,3),(-4,0),(2.4,3),(-4,0),(2.3,3),(-3,0),                 # warm-up decline
      (5,0),(-2.9,4),(5,0),(-3.0,4),(5,0),                                  # impulse up
      (-3.6,0),(2.0,3),(-3.8,0),(2.2,3),(-3.4,0),                           # swing pullback
      (3.4,0),(-2.1,3),(3.8,0),(-2.2,3),(5,0)]                              # back in line, break the swing high
def legs():
    for d,n in LEGS:
        if n:            # a plain pullback
            yield d,n
        else:            # a trend leg in small steps (fractal highs / lows inside it)
            yield d*0.6,3; yield -d*0.12,2; yield d*0.52,3
def make(seed=3, noise=0.1):
    random.seed(seed)
    path=[120.0]
    for d,n in legs():
        s=path[-1]
        for t in range(1,n+1): path.append(s+d*t/n+random.uniform(-noise,noise))
    c=[];prev=path[0]
    for p in path[1:]:
        o=prev; cl=p
        h=max(o,cl)+random.uniform(0.05,0.3); l=min(o,cl)-random.uniform(0.05,0.3)
        c.append((round(o,2),round(h,2),round(l,2),round(cl,2))); prev=cl
    return c
