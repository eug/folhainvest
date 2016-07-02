# -*- coding: utf-8 -*-

import requests
import re
from bs4 import BeautifulSoup
from collections import namedtuple


Portfolio = namedtuple('Portfolio', 'portfolio overview annual_profit monthly_profit')
Stock = namedtuple('Stock', 'symbol name quantity avg_value current_value total_value profit variation')
Profitability = namedtuple('Profitability', 'initial_position current_position current_performance')
Overview = namedtuple('Overview', 'total_capital total_stocks total')

Info = namedtuple('Info', 'capital daily_limit remaining_limit monthly_ranking annual_ranking')
OrderStatus = namedtuple('OrderStatus', 'id type symbol quantity value expiration_date status')
Quote = namedtuple('Quote', 'symbol name last_trade trade_time variation open close high low volume')
SimulatorTrade = namedtuple('SimulatorTrade', 'symbol executed pending total')
Status = namedtuple('Status', 'status_code description')


class FolhaInvest(object):
  """docstring for FolhaInvest"""

  def __init__(self):
    super(FolhaInvest, self).__init__()
    self._session = requests.session()
    self._host = 'http://folhainvest.folha.uol.com.br'


  def _geturl(self, page):
    return '%s/%s' % (self._host, page) 


  def _cast_float(self, text):
    return float(text.replace('.', '').replace(',', '.'))


  def _cast_int(self, text):
    return int(text.replace('.', ''))


  def _cast_rank(self, text):
    return self._cast_int(text.split(' ')[0])


  def _cast_currency(self, text):
    return self._cast_float(text.strip().split(' ')[1])


  def _cast_percentage(self, text):
    return self._cast_float(text.replace('%', ''))


  def login(self, email, password):
    url = 'http://login.folha.com.br/login?done=http://folhainvest.folha.uol.com.br/carteira&service=folhainvest'
    
    payload = {
      'email': email,
      'password': password,
      'auth': 'Autenticar'
    }

    r = self._session.post(url, data=payload)

    # Verifica se foi possivel realizar o login
    if not 'FOLHA_KEY' in r.headers['set-cookie']:
      status_code = 'FAIL'
      description = 'Unable to login'      
    else:
      status_code = 'OK'
      description = 'Successfully logged in'

    return Status(
      status_code = status_code,
      description = description
    )  
    

  def info(self):
    url = self._geturl('ordens')
    r = self._session.get(url)

    html = BeautifulSoup(r.text)
    user_info = html.select('#userInfo')[0].select('p')
    
    monthly_ranking = user_info[0].b.extract()
    annual_ranking  = user_info[1].b.extract()
    capital         = user_info[2].b.extract()
    daily_limit     = user_info[3].b.extract()
    remaining_limit = user_info[4].b.extract()

    monthly_ranking = self._cast_rank(user_info[0].string)
    annual_ranking  = self._cast_rank(user_info[1].string)
    capital         = self._cast_currency(user_info[2].string)
    daily_limit     = self._cast_currency(user_info[3].string)
    remaining_limit = self._cast_currency(user_info[4].string)

    return Info(
      capital         = capital,
      daily_limit     = daily_limit,
      remaining_limit = remaining_limit,
      monthly_ranking = monthly_ranking,
      annual_ranking  = annual_ranking
    )


  def buy(self, symbol, value, quantity, expiration_date, pricing='fixed'):
    """ pricing = market or fixed """
    url = self._geturl('comprar')
    return self._order(url, symbol, value, quantity, expiration_date, pricing)


  def buy_start(self, symbol, value, quantity, expiration_date):
    url = self._geturl('start')
    return self._order(url, symbol, value, quantity, expiration_date, start_stop=1)


  def sell(self, symbol, value, quantity, expiration_date, pricing='fixed'):
    url = self._geturl('vender')
    return self._order(url, symbol, value, quantity, expiration_date, pricing, sell=1)


  def sell_stop(self, symbol, value, quantity, expiration_date):
    url = self._geturl('stop')
    return self._order(url, symbol, value, quantity, expiration_date, start_stop=1, sell=1)


  def _order(self, url, symbol, value, quantity, expiration_date, pricing='', start_stop=0, sell=0):
    # Valida os parametros  
    if type(value) is float:
      value = str(value).replace('.', ',')
    elif type(value) is int:
      value = str(float(value)).repalce('.', ',')


    # Cria payload da requisição
    payload = {
      'start_stop'      : start_stop,
      'sell'            : sell,
      'company'         : symbol,
      'value'           : value,
      'quantity'        : quantity,
      'expiration_date' : expiration_date,
      'execute'         : 'Executar'
    }

    if pricing:
      payload['pricing'] = pricing

    r = self._session.post(url, data=payload)

    # Checa se algum erro ocorreu
    warning = BeautifulSoup(r.text).find(class_='message warning')

    if warning:
      status_code = 'FAIL'
      description = warning.h2.string
    else:
      status_code = 'OK'
      description = 'Order sent'
      # Confirma automaticamente
      self._session.post(r.url, data={ 'confirm': 'Confirmar' })

    return Status(
      status_code = status_code,
      description = description
    )


  def cancel(self, orders_id):
    # orders_id is a list
    url = self._geturl('ordens')

    payload = { 'cancel' : 'Remover ordens' }
    for id in orders_id:
      payload['orders[]'] = id

    r = self._session.post(url, data=payload)


    # TODO: Return status
    return Status(
      status_code = None,
      description = None
    )


  def orders_status(self, filter='all'):
    """ filter = all, cancelled, executed, pendent
    return lista de OrderStatus """
    url = self._geturl('ordens?f=' + filter)
    r = self._session.post(url)
    result = []

    html = BeautifulSoup(r.text)
    for row in html.select('table.fiTable')[0].select('tr')[1:]: # skip header
      cols  = row.select('td')

      id              = int(cols[0].input['value'])
      type            = str(cols[1].b.string)
      symbol          = str(cols[2].b.string)
      quantity        = self._cast_int(cols[3].string)
      value           = self._cast_float(cols[4].string)
      expiration_date = str(cols[5].string)
      status          = str(cols[6].b.string)

      order_status = OrderStatus(
        id              = id,
        type            = type,
        symbol          = symbol,
        quantity        = quantity, 
        value           = value,
        expiration_date = expiration_date,
        status          = status
      )

      result.append(order_status)

    return result


  def portfolio(self):
    url = self._geturl('carteira')
    r = self._session.get(url)

    # TODO: Implementar



  def reset_portfolio(self):
    url = self._geturl('limpar')
    r = self._session.get(url)

    payload = { 'confirm': 'Confirmar' } # cancel:Cancelar
    self._session.post(r.url, data=payload)

    # TODO: Return status
    return Status(
      status_code=None,
      description=None
    )


  def get_portfolio_csv(self, filename):
    url = self._geturl('carteira?tsv=yes')
    r = self._session.get(url)
    with open(filename, 'wb') as f:
      for chunk in r.iter_content(chunk_size=1024): 
        if chunk: # filter out keep-alive new chunks
          f.write(chunk)

    # TODO: Return status code
    return Status(
      status_code=None,
      description=None
    )


  def quotations(self, view=''):
    # view: '' or 'portfolio'
    url = self._geturl('cotacoes?view_option=' + view)
    r = self._session.get(url)
    result = []

    html = BeautifulSoup(r.text)
    for row in html.select('table.fiTable')[0].select('tr')[1:]: # skip header
      cols = row.select('td')

      symbol     = str(cols[1].b.string)
      name       = str(cols[3].string)
      last_trade = self._cast_float(cols[5].string)
      trade_time = str(cols[6].string)
      variation  = self._cast_percentage(cols[7].string)
      open       = self._cast_float(cols[8].string)
      close      = self._cast_float(cols[9].string)
      high       = self._cast_float(cols[10].string)
      low        = self._cast_float(cols[11].string)
      volume     = self._cast_int(cols[12].string)

      quote = Quote(
        symbol     = symbol,
        name       = name,
        last_trade = last_trade,
        trade_time = trade_time,
        variation  = variation,
        open       = open,
        close      = close,
        high       = high,
        low        = low,
        volume     = volume
      )

      result.append(quote)

    return result


  def simulator_trades(self):
    url = self._geturl('negociacoes')
    r = self._session.get(url)
    result = []

    html = BeautifulSoup(r.text)
    
    # remove useless tables
    [m.extract() for m in html.find_all('table', class_='marker')]

    # skip first and last items of the list
    for row in html.find('table', class_='logTable').select('tr')[1:-1]:
      cols = row.select('td')
      
      symbol   = ''.join(re.findall('\>(.*?)\<', str(cols[0].a)))
      executed = self._cast_int(cols[1].string)
      pending  = self._cast_int(cols[2].string)
      total    = self._cast_int(cols[3].string)

      simulator_trade = SimulatorTrade(
        symbol   = symbol,
        executed = executed, 
        pending  = pending,
        total    = total
      )

      result.append(simulator_trade)

    return result


  # def bank_statement(self):
  #   print 'Not implemented yet'

  # def company_info(self, symbol, section=''):
  #   # section: '' or 'history'
  #   # year: ''
  #   print 'Not implemented yet'

  # def ranking(self):
  #   print 'Not implemented yet'
    
  # def controlling_interest(self):
  #   print 'Not implemented yet'