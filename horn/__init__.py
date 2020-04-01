from re import compile
from copy import deepcopy


class Unit:
    """
    Unit是表达式中最基本的单元，其遵循以下规则：
    1) 所有名字皆为英文字母和_的组合
    2) 代表全体变量需要在变量名前加上*
    eg: fun(a, *b)，fun代表属性，a代表个体，*b代表全体
    """
    __pattern = compile(r'^\s*(.*)\s*\((.*)\)\s*$')
    __name_pattern = compile(r'^\w+$')
    __arg_pattern = compile(r'^\*?\w+$')
    __global_arg_pattern = compile(r'^\*\w+$')

    def __init__(self, unit: str):
        res = Unit.__pattern.match(unit)

        assert Unit.__name_pattern.match(res.group(1))
        self.name = res.group(1)

        self.args = []
        for each in res.group(2).split(','):
            each = each.strip()
            res = Unit.__arg_pattern.match(each)
            self.args.append(res.group())

    def mapping_args(self, other):
        """
        返回self映射至other需要修改的变量，结果是一个字典，键值对为(old, new)
        eg: f(*a, *b) mapping_args f(c, d)  返回：{'*a':'c', '*b':'d'}
            f(a, b) mapping_args f(*c, *d)  将会抛出异常
        """
        # assert isinstance(other, Unit)
        assert self.name == other.name
        assert len(self.args) == len(other.args)

        # 对应的个体变量应该相等
        for each in zip(self.args, other.args):
            if not Unit.__global_arg_pattern.match(each[0]):
                assert each[0] == each[1]

        # 建立self表达式的各个全体变量的映射
        li = [each for each in zip(self.args, other.args) if Unit.__global_arg_pattern.match(each[0])]
        di = dict(li)
        # 可能存在如下情况：
        # f(*a, *a) mapping_args f(b, c)
        # 该情况是映射失败的情况，因为映射后*a不可能既是b又是c
        # 此时 li = [('*a', 'b'), ('*a', 'c')], di = {'*a': 'c'}
        # 所以，判断li中的所有映射是否仍然在di中即可
        items = di.items()
        for each in li:
            assert each in items

        return di

    def __eq__(self, other):
        try:
            # 如果self能映射到other，并且映射到的所有other变量都是全体的，那么这两个等价
            res = self.mapping_args(other)
            for each in res:
                if not Unit.__global_arg_pattern.match(each):
                    return False
            return True
        except AssertionError:
            return False

    def __contains__(self, item):
        return self == item

    def __str__(self):
        return self.name + '(' + ','.join(self.args) + ')'


class Expression:
    """
    表达式在推理机中组成库，其遵循一下原则：
    1) Unit<-Unit1^Unit2^.^UnitN，其中Unit的规则请转到Unit文档查看详情
    """
    __pattern = compile(r'^(.*)<-(.*)$')

    def __init__(self, expression: str):
        res = Expression.__pattern.match(expression)

        self.head = None if res.group(1).strip() == '' else Unit(res.group(1))

        self.body = []
        if res.group(2).strip() != '':
            for each in res.group(2).split('^'):
                self.body.append(Unit(each))

    def mix(self, unit: Unit):
        """
        返回self和unit的消解结果，其结果等价于self和一个无头子句的消解结果，如果无法消解则抛出异常
        eg: f(*a)<-g(*a) mix f(John) <=> f(*a)<-g(*a) mix <-f(John)
        """
        assert unit.name == self.head.name
        assert len(unit.args) == len(self.head.args)

        di = self.head.mapping_args(unit)

        ret = deepcopy(self)
        ret.head = None
        for u in ret.body:
            for each in di:
                for i in range(u.args.count(each)):
                    u.args[u.args.index(each)] = di[each]

        return ret

    def __str__(self):
        return (str(self.head) if self.head else '') + '<-' + (
            '^'.join(str(each) for each in self.body) if len(self.body) else '')


class Engine:
    def __init__(self, lib):
        self.lib = []
        self.terminate = []
        for each in lib:
            exp = Expression(each)
            if not exp.head:
                # 无头子句，是递归中止的条件
                self.terminate.append(exp)
            else:
                self.lib.append(exp)

    def __proof(self, exp: Expression):
        assert not exp.head
        if not len(exp.body):
            return []

        # 如果有任意的待证目标位于terminate中，则应该中止，返回None
        # TODO

        for each in exp.body:
            for regular in self.lib:
                try:
                    res = regular.mix(each)  # 尝试消解
                    copy = deepcopy(exp)  # 消解成功
                    copy.body.remove(each)
                    res.body.extend(copy.body)
                    ret = self.__proof(res)
                    if ret is not None:
                        ret.insert(0, (regular, res))
                        return ret
                except AssertionError:
                    pass

    def proof(self, exp: str):
        """
        返回消解过程，如果无法消解，则返回None
        """
        exp = Expression(exp)
        assert not exp.head
        self.terminate.append(exp)
        ret = self.__proof(exp)
        self.terminate.pop()
        # if ret:
        #     ret.insert(0, exp)
        return ret


if not __debug__:
    raise BaseException
