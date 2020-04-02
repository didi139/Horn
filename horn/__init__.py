from re import compile
from copy import deepcopy


class Unit:
    """
    Unit是表达式中最基本的单元，其遵循以下规则：
    1) 所有名字皆为英文字母和_的组合
    2) 代表全体变量需要在变量名前加上*
    eg: fun(a, *b)，fun代表属性，a代表个体，*b代表全体
    """
    _pattern = compile(r'^\s*(.*)\s*\((.*)\)\s*$')
    _name_pattern = compile(r'^\w+$')
    _arg_pattern = compile(r'^\*?\w+$')

    @classmethod
    def _is_global_arg(cls, arg: str) -> bool:
        return arg.startswith('*')

    def __init__(self, unit: str):
        res = Unit._pattern.match(unit)

        assert Unit._name_pattern.match(res.group(1))
        self.name = res.group(1)

        self.args = []
        for each in res.group(2).split(','):
            each = each.strip()
            res = Unit._arg_pattern.match(each)
            self.args.append(res.group())

    def update_args(self, mapping: dict):
        for i in range(len(self.args)):
            self.args[i] = mapping.get(self.args[i], self.args[i])

    def mapping_args0(self, other):
        """
        self和other合并，分别需要修改什么变量，其中如果变量皆为全体那么名字以other的为主
        如果self中一个全体变量对应other中的多个全体变量，那么other中需要将其统一
        eg: f(*a, *b, c, *b) mapping_args f(d, *e, *f, *g)
            *b 对应 *e和*g，所以other需要将*e改为*g
            返回 ({'*a':'d', '*b':'*g'},{'*f':'c', '*e':'*g'})
        """
        if not isinstance(other, Unit):
            return None
        if self.name != other.name:
            return None
        if len(self.args) != len(other.args):
            return None

        self_map = {}
        other_map = {}
        for s, o in zip(self.args, other.args):
            s_is_global = Unit._is_global_arg(s)
            o_is_global = Unit._is_global_arg(o)
            if s_is_global:
                # self_map中可能存在一个全体映射到多个个体的可能，用集合收集起来
                self_map[s] = self_map.get(s, set())
                self_map[s].add(o)
            elif o_is_global:
                # other_map只存在从全体映射到个体的可能
                if other_map.get(o, s) != s:
                    return None
                other_map[o] = s
            elif s != o:
                return None

        for k, v in self_map.items():
            if len(v) == 1:
                self_map[k] = v.pop()
            else:
                # k存在多个映射，以某种方式将他们进行排序，然后取li[-1]作为最终映射目标
                li = sorted(list(v), key=lambda t: t)
                self_map[k] = li[-1]
                for i in range(len(li) - 1):
                    if other_map.get(li[i], li[-1]) != li[-1]:
                        return None
                    other_map[li[i]] = li[-1]

        return self_map, other_map

    def mapping_args(self, other):
        """
        返回self映射至other需要修改的变量，如果可以映射结果是一个字典，否则为None
        eg: f(*a, *b) mapping_args f(c, d)  返回：{'*a':'c', '*b':'d'}
            f(a, b) mapping_args f(*c, *d)  返回：None
        :type other: Unit
        """
        if not isinstance(other, Unit):
            return None
        if self.name != other.name:
            return None
        if len(self.args) != len(other.args):
            return None

        # 对应的个体变量应该相等
        for each in zip(self.args, other.args):
            if not Unit._is_global_arg(each[0]):
                if each[0] != each[1]:
                    return None

        # 建立self表达式的各个全体变量的映射
        li = [each for each in zip(self.args, other.args) if Unit._is_global_arg(each[0])]
        di = dict(li)
        # 可能存在如下情况：
        # f(*a, *a) mapping_args f(b, c)
        # 该情况是映射失败的情况，因为映射后*a不可能既是b又是c
        # 此时 li = [('*a', 'b'), ('*a', 'c')], di = {'*a': 'c'}
        # 所以，判断li中的所有映射是否仍然在di中即可
        items = di.items()
        for each in li:
            if each not in items:
                return None

        return di

    def __eq__(self, other):
        """
        :type other: Expression
        """
        if not isinstance(other, Unit):
            return False
        return str(self) == str(other)

    def __le__(self, other):
        """
        判断self是否含于other
        eg: fun( a, *b) <= fun(*c, *d)      True
            fun( a, *b) <= fun( c, *d)      False
            fun( a, *b) <= fun(*c,  d)      False
            fun( a,  b) <= fun(*c, *c)      False
            fun( a,  b) <= fun( a,  b)      True
        """
        if not isinstance(other, Unit):
            return False
        return other.mapping_args(self) is not None

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

    def update_args(self, mapping: dict):
        if self.head:
            self.head.update_args(mapping)
        for each in self.body:
            each.update_args(mapping)

    def remove_all_from_body(self, unit: Unit):
        for i in range(self.body.count(unit)):
            self.body.remove(unit)

    def mix(self, other):
        """
        self和other关于的消解结果，有以下两种情况
        eg: 1) self = <-f(a)^g(b)
               other = f(*c)<-k(*c,d)
               self mix other = <-k(a,d)^g(b)
               这种情况为假设<-f(a)，则<-k(a,d)^g(b)
            2) self = <-f(*a)^g(*a,b)
               other = f(c)<-
               self mix other = <-g(c,b)
               这种情况为other为真事实，缩小self中*a的范围，也是一种假设
        :type other: Expression
        """
        if not isinstance(other, Expression):
            return None

        if self.head or not other.head:
            return None

        # 情况1
        for each in self.body:
            mapping = other.head.mapping_args(each)
            if mapping is not None:
                # 该位置可进行映射
                copy = deepcopy(other)
                copy.head = None
                copy.update_args(mapping)
                copy.body.extend([each for each in self.body if each not in copy.body])
                copy.remove_all_from_body(each)
                return copy

        # 情况2
        if not other.body:
            for each in self.body:
                mapping = each.mapping_args(other.head)
                if mapping:
                    copy = deepcopy(self)
                    copy.remove_all_from_body(each)
                    copy.update_args(mapping)
                    return copy

        return None

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

    def _proof(self, exp: Expression):
        if exp.head:
            return None

        if not exp.body:
            return []

        # 如果有任意的待证目标位于terminate中，则应该中止，返回None
        # for cond in self.terminate:
        #     names = {each.name for each in exp.body}
        #     lic = sorted([each for each in cond.body if each.name in names], key=lambda t: str(t))
        #     lie = sorted(exp.body[:], key='')
        #
        #     if len(li) == len(exp.body):
        #         for e in exp.body:
        #             for l in li:
        #                 if e >= l:
        #                     established = False
        #     established = True  # 任意在exp中的变量是否都在cond中
        #     for unit in exp.body:
        #         if unit.
        #     while established:
        #
        #     {str(each): each for each in exp}.values()
        #     for s, o in zip(exp.body, cond.body):
        #         pass

        for i, each in enumerate(self.lib):
            i += 1
            res = exp.mix(each)
            if res:
                ret = self._proof(res)
                if ret is not None:
                    ret.insert(0, (each, res))
                    return ret

        return

    def proof(self, exp: str):
        """
        返回消解过程，如果无法消解，则返回None
        """
        exp = Expression(exp)
        # self.terminate.append(exp)
        ret = self._proof(exp)
        # self.terminate.pop()
        return ret
