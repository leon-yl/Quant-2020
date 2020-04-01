# 克隆自聚宽文章：https://www.joinquant.com/post/1399
# 标题：【量化课堂】多因子策略入门
# 作者：JoinQuant量化课堂

# 导入函数库
from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
      # 开盘时运行
    run_daily(market_open, time='open', reference_security='000300.XSHG')
      # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

    # parameters
    g.tc = 15 #调仓频率
    g.sampleLen = 63 # day
    g.holdNum = 20 # hold stock No
    g.factors = ['market_cap','roe']
    # 因子等权重里1表示因子值越小越好，-1表示因子值越大越好

    g.weights = [[1],[-1]] # factors equalily weight,1 the samller the better
    g.t = 0   # trade tag
    g.if_trade = False # record current day wether or not trading

## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：'+str(context.current_dt.time()))
    # 做取模运算，即看是否交易次数达到了调仓频率
    if g.t % g.tc == 0:
        # 记录今日进行交易
        g.if_trade = True
        # 设置可行股票池：获得当前开盘的沪深300股票池并剔除当前或者计算样本期间停牌的股票
        # stock_list设置为沪深300的指数成分股，get_index_stocks('000300.XSHG')实现
        g.all_stocks = set_feasible_stocks(get_index_stocks('000300.XSHG'),g.sampleLen,context)
        # 查询上述股票池的相应数据
        g.q = query(valuation,balance,cash_flow,income,indicator).filter(valuation.code.in_(g.all_stocks))
    # 开盘前 tag+1，记录该函数的运行次数
    g.t += 1
# 这整个函数的作用为，在每次开盘前检测是否达到了调仓频率，达到了即做调整
# 调用set_feasible_stocks()函数进行t

# 调整所持有股票池，并剔除停牌股票
def set_feasible_stocks(stock_list,days,context):
    suspended_info_df = get_price(list(stock_list),start_date = context.current_dt,end_date = context.current_dt,frequency='daily',fields = 'paused')['paused'].T
    # unsuspended_index = suspended_info_df.loc[:,0] == 0# 1 suspended 0 unsuspended stocks
    unsuspended_stock = suspended_info_df[suspended_info_df.iloc[:,0] == 0].index
    # making futher getting unsuspended stocks before days
    feasible_stocks = []
    for stock in unsuspended_stock:
        if sum(attribute_history(stock, count=days, unit='1d', fields=('paused'), skip_paused=False, ))[0] == 0:
            feasible_stocks.append(stock)
    return feasible_stocks
  


## 开盘时运行函数
def market_open(context):
    log.info('函数运行时间(market_open):'+str(context.current_dt.time()))
    if g.if_trade==True:
    # 计算现在的总资产，以分配资金，这里是等额权重分配
        g.everyStock=context.portfolio.portfolio_value/g.holdNum

        
        fund_df = get_fundamentals(g.q,context.current_dt)
        # factors 前面g设置的
        res_df = fund_df.set_index('code')[g.factors].copy()

        res_df.fillna(res_df.mean(),inplace = True)
        # 得到排名
        res_rank = res_df.rank(ascending = False)
        # 与weight相乘得到分数
        res_rank.loc[:,'score'] = np.dot(res_rank,g.weights)
        # 按照分数进行排序
        res_rank.sort_values(by = 'score',ascending = False,inplace = True)
        # 按照持股数量进行买卖分割
        toBuy = np.array(res_rank.index)[:g.holdNum]

        # 对于不需要持仓的股票，全仓卖出
        order_stock_sell(context,toBuy)
        # 对于不需要持仓的股票，按分配到的份额买入
        order_stock_buy(context,toBuy)

    g.if_trade=False  
## 收盘后运行函数
def after_market_close(context):
    pass
#6
#获得卖出信号，并执行卖出操作
#输入：context,-list
#输出：none
def order_stock_sell(context,toBuy):
    #如果现有持仓股票不在股票池，清空
    list_position=context.portfolio.positions.keys()
    for stock in list_position:
        if stock not in toBuy:
            order_target(stock, 0)

#7
#获得买入信号，并执行买入操作
#输入：context,-list
#输出：none
def order_stock_buy(context,toBuy):
    # 对于不需要持仓的股票，按分配到的份额买入
    for i in range(0,len(toBuy)):
        # 买卖数量按照当前账户资金平均分配到每个股票
        order_target_value(toBuy[i], g.everyStock)
