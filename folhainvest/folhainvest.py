# -*- coding: utf-8 -*-

import os.path
import re
from collections import defaultdict, namedtuple

import requests
from bs4 import BeautifulSoup

Portfolio = namedtuple('Portfolio', 'stocks overview annual_profit monthly_profit')
Stock = namedtuple('Stock', 'symbol name quantity avg_value current_value total_value profit variation')
Profitability = namedtuple('Profitability', 'initial_position current_position current_performance')
Overview = namedtuple('Overview', 'total_capital total_stocks total')

Info = namedtuple('Info', 'capital daily_limit remaining_limit monthly_ranking annual_ranking')
OrderStatus = namedtuple('OrderStatus', 'id type symbol quantity value expiration_date status')
Quote = namedtuple('Quote', 'symbol name last_trade trade_time variation open close high low volume')
SimulatorTrade = namedtuple('SimulatorTrade', 'symbol executed pending total')
Status = namedtuple('Status', 'status_code description')


class FolhaInvest(object):
  """API de acesso ao FolhaInvest.

  Fornece os principais métodos de acesso à plataforma de simulação, permitindo
  o envio e monitoramento de ordens e a recuperação de informações gerais.

  References
  ----------
  [1] http://folhainvest.folha.uol.com.br
  """

  def __init__(self):
    super(FolhaInvest, self).__init__()
    self._session = requests.session()
    self._host = 'http://folhainvest.folha.uol.com.br'


  def _geturl(self, page):
    """Retorna a url completa para requisição."""
    return '%s/%s' % (self._host, page) 


  def _get_symbol(self, html):
    """Retorna nome da empresa a partir de uma tag html 'a'."""
    return ''.join(re.findall('\>(.*?)\<', str(html)))


  def _cast_float(self, text):
    """Converte uma string para float."""
    return float(text.replace('.', '').replace(',', '.'))


  def _cast_int(self, text):
    """Converte uma string para int."""
    return int(text.replace('.', ''))


  def _cast_rank(self, text):
    """Converte string contendo indicador ordinal para int."""
    return self._cast_int(text.split(' ')[0])


  def _cast_currency(self, text):
    """Converte string no formato de moeda para float."""
    return self._cast_float(text.strip().split(' ')[1])


  def _cast_percentage(self, text):
    return self._cast_float(text.replace('%', ''))


  def login(self, email, password):
    """ Realiza do usuário autenticação no sistema.

    Parameters
    ----------
    email : string
            Email do usuário.

    password : string
            Senha do usuário.

    Returns
    -------
    status : Status
            Retorna o estado da autenticação.
    """
    url = 'http://login.folha.com.br/login?done=http://folhainvest.folha.uol.com.br/carteira&service=folhainvest'
    
    payload = {
      'email'    : email,
      'password' : password,
      'auth'     : 'Autenticar'
    }

    r = self._session.post(url, data=payload)

    # Verifica se foi possivel realizar o login
    if 'FOLHA_KEY' in r.headers['set-cookie']:
      status_code = 'OK'
      description = 'Login efetuado com sucesso'
    else:
      status_code = 'FAIL'
      description = 'Não foi possível efetuar o login'      

    return Status(
      status_code = status_code,
      description = description
    )  
    

  def info(self):
    """Retorna informações gerais do desempenho.

    Returns
    -------
    info : Info
          Retorna os valores em uma tupla.
    """
    url = self._geturl('ordens')
    r = self._session.get(url)

    html = BeautifulSoup(r.text)
    user_info = html.select('#userInfo')[0].select('p')
    
    # Remove tags desnecessárias
    user_info[0].b.extract()
    user_info[1].b.extract()
    user_info[2].b.extract()
    user_info[3].b.extract()
    user_info[4].b.extract()

    # Extrai dados e converte para os tipos apropriados
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
    """Envia uma ordem de compra.

    Parameters
    ----------
    symbol : string
            Nome da empresa (ex. ABEV3, PETR4, etc).
    
    value : string ou float
            Valor da compra (ex. '12,45' ou 12.45).
    
    quantity : string ou int
            Volume da compra (ex. '1.000' ou 1000).
    
    expiration_date : string
            Data de vencimento da compra (ex. '31/12/2100').
    
    pricing : 'fixed' ou 'market' (default='fixed')
            Tipo de preço da compra, preço fixo ('fixed') ou a mercado ('market').
  
    Returns
    -------
    status : Status
             Retorna o estado da submissão.
    """
    url = self._geturl('comprar')
    return self._order(url, symbol, value, quantity, expiration_date, pricing)


  def buy_start(self, symbol, value, quantity, expiration_date):
    """Envia um start de compra.

    Parameters
    ----------
    symbol : string
            Nome da empresa (ex. ABEV3, PETR4, etc).
    
    value : string ou float
            Valor da compra (ex. '12,45' ou 12.45).
    
    quantity : string ou int
            Volume da compra (ex. '1.000' ou 1000).
    
    expiration_date : string
            Data de vencimento da venda (ex. '31/12/2100').
    
    Returns
    -------
    status : Status
            Retorna o estado da submissão.
    """
    url = self._geturl('start')
    return self._order(url, symbol, value, quantity, expiration_date, start_stop=1)


  def sell(self, symbol, value, quantity, expiration_date, pricing='fixed'):
    """Envia uma ordem de venda.

    Parameters
    ----------
    symbol : string
            Nome da empresa (ex. ABEV3, PETR4, etc).
    
    value : string ou float
            Valor da venda (ex. '12,45' ou 12.45).
    
    quantity : string ou int
            Volume da venda (ex. '1.000' ou 1000).
    
    expiration_date : string
            Data de vencimento da venda (ex. '31/12/2100').
    
    pricing : 'fixed' ou 'market' (default='fixed')
            Tipo de preço da venda, preço fixo ('fixed') ou a mercado ('market').
  
    Returns
    -------
    status : Status
            Retorna o estado da submissão.
    """
    url = self._geturl('vender')
    return self._order(url, symbol, value, quantity, expiration_date, pricing, sell=1)


  def sell_stop(self, symbol, value, quantity, expiration_date):
    """Envia um stop de venda.

    Parameters
    ----------
    symbol : string
            Nome da empresa (ex. ABEV3, PETR4, etc).
    
    value : string ou float
            Valor da venda (ex. '12,45' ou 12.45).
    
    quantity : string ou int
            Volume da venda (ex. '1.000' ou 1000).
    
    expiration_date : string
            Data de vencimento da venda (ex. '31/12/2100').
    
    Returns
    -------
    status : Status
            Retorna o estado da submissão.
    """
    url = self._geturl('stop')
    return self._order(url, symbol, value, quantity, expiration_date, start_stop=1, sell=1)


  def _order(self, url, symbol, value, quantity, expiration_date, pricing='', start_stop=0, sell=0):
    """Método genérico para envio de ordens.

    Atenção: Este método não deve ser chamado diretamente, deve ser restrito
    ao uso interno da classe.

    Parameters
    ----------
    url : string
            URL da requisição.

    symbol : string
            Nome da empresa (ex. ABEV3, PETR4, etc).

    value : string ou float
            Valor da ordem (ex. '12,45' ou 12.45).

    quantity : string ou int
            Volume da ordem (ex. '1.000' ou 1000).

    expiration_date : string
            Data de vencimento da ordem (ex. '31/12/2100').

    pricing : '', 'fixed' ou 'market' (default='')
            Tipo de preço da ordem. Define 'fixed' para usar preço fixo,
            'market' para preço a mercado e '' para operações stop de venda,
            ou start de compra.

    start_stop : 0 ou 1 (default=0)
            Quando definido para 0 ativa operação start, e 1 ativa operação
            stop. Deve ser usado em combinação com o parâmetro 'sell'.

    sell : 0 ou 1 (default=0)
            Quando definido para 0 ativa operação de compra, e 1 ativa operação
            de venda. Deve ser usado em combinação com o parâmetro 'start_stop'.

    Returns
    -------
    status : Status
            Retorna o estado da submissão.
    """
    # Valida os parâmetros  
    if type(value) is float:
      value = str(value).replace('.', ',')
    elif type(value) is int:
      value = str(float(value)).replace('.', ',')
    elif type(value) is str:
      value = value.replace('.', ',')

    if type(quantity) is float:
      quantity = int(quantity)

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

    # Adiciona 'pricing' ao payload quando definido
    if pricing:
      payload['pricing'] = pricing

    r = self._session.post(url, data=payload)

    # Checa se algum erro ocorreu
    warning = BeautifulSoup(r.text).find(class_='message warning')

    if not warning:
      status_code = 'OK'
      description = 'Ordem enviada com sucesso'
      self._session.post(r.url, data={ 'confirm': 'Confirmar' })
    else:
      status_code = 'FAIL'
      description = warning.h2.string

    return Status(
      status_code = status_code,
      description = description
    )


  def cancel(self, orders_id):
    """Envia uma ordem de cancelamento.
    
    Parameters
    ----------
    orders_id : list
            Uma lista de id's de cada ordem a ser cancelada. Se uma lista
            vazia for fornecida, a ordem não é enviada. Caso valores
            inválidos forem especificados, os possíveis erros não serão
            retornados por este método.

    Returns
    -------
    status : Status
            Retorna o estado da submissão.
    """
    payload = defaultdict(list)
    for id in orders_id:
      payload['orders[]'].append(id)
    payload['cancel'].append('Remover ordens')

    url = self._geturl('ordens')
    r = self._session.post(url, data=payload)

    if r.status_code == 200 and len(payload) > 1:
      status_code = 'OK'
      description = 'Requisição enviada com sucesso'
    else:
      status_code = 'FAIL'
      description = 'Falha no envio da requisição'

    return Status(
      status_code = status_code,
      description = description
    )


  def orders_status(self, filter='all'):
    """Retorna o estado das ordens enviadas.
    
    Atenção: Para ordens enviadas a mercado os valores de compra/venda serão
    fixados para 0 (zero).

    Parameters
    ----------
    filter : 'all', 'cancelled', 'executed', 'pendent' (default='all')
            Filtra ordens pelo respectivo estado.

    Returns
    -------
    orders_status : list
            Retorna lista de OrderStatus contendo informações de cada
            ordem. Retorna uma lista vazia, caso nenhuma ordem seja
            encontrada.
    """
    url = self._geturl('ordens?f=' + filter)
    r = self._session.post(url)
    result = []

    html = BeautifulSoup(r.text)
    for row in html.select('table.fiTable')[0].select('tr')[1:]:
      cols  = row.select('td')

      id              = int(cols[0].input['value'])
      type            = str(cols[1].b.string)
      symbol          = str(cols[2].b.string)
      quantity        = self._cast_int(cols[3].string)
      value           = cols[4].string
      expiration_date = str(cols[5].string)
      status          = str(cols[6].b.string)

      # Valores a mercado são definidos para 0
      if 'mercado' in value:
        value = 0.0
      else:
        value = self._cast_float(value)

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
    """Retorna informações referentes a carteira.

    Returns
    -------
    portfolio : Portfolio
            Retorna uma tupla Portfolio contendo as informações encontradas.
    """
    url = self._geturl('carteira')
    r = self._session.get(url)
    html = BeautifulSoup(r.text)

    tables = html.select('table.fiTable')
    table_stocks         = tables[0]
    table_overview       = tables[1]
    table_annual_profit  = tables[2]
    table_monthly_profit = tables[3]

    # Extrai informações de ações da carteira
    stocks = []
    for row in table_stocks.select('tr')[1:-1]:
      cols = row.select('td')

      symbol        = self._get_symbol(cols[0])
      name          = cols[1].string
      quantity      = self._cast_int(cols[4].string)
      avg_value     = self._cast_float(cols[5].string)
      current_value = self._cast_float(cols[6].string)
      total_value   = self._cast_float(cols[7].string)
      profit        = self._cast_float(cols[8].string)
      variation     = self._cast_float(cols[9].string)

      stock = Stock(
        symbol        = symbol,
        name          = name,
        quantity      = quantity,
        avg_value     = avg_value,
        current_value = current_value,
        total_value   = total_value,
        profit        = profit,
        variation     = variation
      )
      stocks.append(stock)

    # Extrai informações gerais
    cols = table_overview.select('tr')[1].select('td')
    total_capital = self._cast_float(cols[0].string)
    total_stocks  = self._cast_float(cols[1].string)
    total         = self._cast_float(cols[2].string)

    overview = Overview(
      total_capital = total_capital,
      total_stocks  = total_stocks,
      total = total
    )

    # Extrai Rentabilidade Anual
    rows = table_annual_profit.select('tr')[1:]
    a_initial_position    = self._cast_float(rows[0].select('td')[1].string)
    a_current_position    = self._cast_float(rows[1].select('td')[1].string)
    a_current_performance = self._cast_percentage(rows[2].select('td')[1].string)

    annual_profit = Profitability(
      initial_position    = a_initial_position,
      current_position    = a_current_position,
      current_performance = a_current_performance
    )

    # Extrai Rentabilidade Mensal
    rows = table_monthly_profit.select('tr')[1:]
    m_initial_position    = self._cast_float(rows[0].select('td')[1].string)
    m_current_position    = self._cast_float(rows[1].select('td')[1].string)
    m_current_performance = self._cast_percentage(rows[2].select('td')[1].string)

    monthly_profit = Profitability(
      initial_position    = m_initial_position,
      current_position    = m_current_position,
      current_performance = m_current_performance
    )

    return Portfolio(
      stocks         = stocks,
      overview       = overview,
      annual_profit  = annual_profit,
      monthly_profit = monthly_profit
    )


  def reset_portfolio(self):
    """Reinicia a carteira.

    Returns
    -------
    status : Status
            Retorna o estado da submissão.
    """
    url = self._geturl('limpar')
    r = self._session.get(url)

    # Confirma automaticamente
    r = self._session.post(r.url, data={ 'confirm': 'Confirmar' })

    if r.status_code == 200:
      status_code = 'OK'
      description = 'Requisição enviada com sucesso'
    else:
      status_code = 'FAIL'
      description = 'Falha no envio da requisição'

    return Status(
      status_code = status_code,
      description = description
    )


  def get_portfolio_csv(self, filepath='carteira.xls'):
    """Realiza o download da carteira no formato'.xls'.

    Parameters
    ----------
    filepath : string (default='carteira.xls')
            Contém o caminho e nome com formato do arquivo
            (ex. '/caminho/carteira.xls').

    Returns
    -------
    status : Status
            Retorna o estado do download.
    """
    url = self._geturl('carteira?tsv=yes')
    r = self._session.get(url)

    if r.status_code == 200:
      with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
          if chunk:
            f.write(chunk)

    if os.path.exists(filepath):
      status_code = 'OK'
      description = 'Arquivo obtido com sucesso'
    else:
      status_code = 'FAIL'
      description = 'Não foi possível obter arquivo'

    return Status(
      status_code = status_code,
      description = description
    )


  def quotations(self, view=''):
    """Retorna as cotações.

    Parameters
    ----------
    view : '' ou 'portfolio', (default='')
            Lista todas as empresas ('') ou somente empresas existentes na
            carteira ('portfolio').

    Returns
    -------
    quotations : list
            Retorna lista de Quote contendo a cotação de cada empresa.
            Um lista vazia é retornada quando não for possível encontrar
            cotações.
    """
    url = self._geturl('cotacoes?view_option=' + view)
    r = self._session.get(url)
    result = []

    html = BeautifulSoup(r.text)
    for row in html.select('table.fiTable')[0].select('tr')[1:]:
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
    """Retorna o número de negociações feitas em cada empresa no simulador.

    Returns
    -------
    simulator_trades : list
            Retorna uma lista de objetos SimulatorTrade contendo o número
            de negociações realizadas no simulador em cada empresa. Uma lista
            vazia é retornada caso nenhum valor seja encontrado.
    """
    url = self._geturl('negociacoes')
    r = self._session.get(url)
    result = []

    html = BeautifulSoup(r.text)

    # Remove tabelas desnecessárias
    [m.extract() for m in html.find_all('table', class_='marker')]

    # Ignora primeira e última posição da lista
    for row in html.find('table', class_='logTable').select('tr')[1:-1]:
      cols = row.select('td')

      symbol   = self._get_symbol(cols[0].a)
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