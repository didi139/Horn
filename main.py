import horn

# e1 = horn.Expression('<-f(c,*d)^g(c,*d)')
# e2 = horn.Expression('f(*a, b)<-k(e,f)')
# print(e1.mix(e2))

engine = horn.Engine([
    'lucky(john)<-',
    '<-study(john)',
    'happy(*X)<-pass(*X,history)^win(*X,lottery)',
    'pass(*Y,*Z)<-study(*Y)',
    'pass(*W,*V)<-lucky(*W)',
    'win(*U,lottery)<-lucky(*U)'
])

res = engine.proof('<-happy(john)')
print('证明：<-happy(john)')
for each in res:
    print('结合：', str(each[0]).center(30), '，生成：', str(each[1]).center(30))
