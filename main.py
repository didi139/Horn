import horn

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
# [each[0] for each in res]
# [each[1] for each in res]
for each in res:
    print('结合：', str(each[0]).center(30), '，生成：', str(each[1]).center(30))
