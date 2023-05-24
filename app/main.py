from flask import Flask, request, Response
from datetime import datetime
from waitress import serve
from emoji import replace_emoji
from os import getenv
from time import sleep
from threading import Thread
from requests import get, post, put, delete, RequestException

class API:
    def __init__(self, token, url, endpoint):
        self._h = {'accept': 'application/json', 'Authorization': f'Bearer {token}'}
        self._u = f'{url}/api/v1/'
        self._p = endpoint
        
    def ping(self):
        try:
            r = get(f'{self._u}{self._p}', headers=self._h)
            r.raise_for_status()
            return True
        except:
            return False

    def _get(self, e):
        try:
            r = get(f'{self._u}{e}', headers=self._h)
            r.raise_for_status()
            return r.json()['data']
        except RequestException:
            print(r.text)
            
    def _delete(self, e):
        try:
            r = delete(f'{self._u}{e}', headers=self._h)
            r.raise_for_status()
        except RequestException:
            print(r.text)
        
    def _post(self, e, pl):
        try:
            r = post(f'{self._u}{e}', headers=self._h, json=pl)
            r.raise_for_status()
            return r.json()['data']
        except RequestException:
            print(r.text)
    
    def _put(self, e, pl):
        try:
            r = put(f'{self._u}{e}', headers=self._h, json=pl)
            r.raise_for_status()
            return r.json()['data']
        except RequestException:
            print(r.text)
    
class Up(API):
    def __init__(self, token, wh):
        super().__init__(token, 'https://api.up.com.au', 'util/ping')
        self._wh = wh
        
    def wh_exists(self):
        try:
            whs = self._get('webhooks')
            for w in whs:
                if w['attributes']['url'] == self._wh:
                    return True
                return False
        except:
            return False
    
    def create_wh(self):
        self._post('webhooks', {'data': {'attributes': {'url': self._wh, 'description': 'FireUp'}}})
        
    def cats(self):
        data = {}
        for c in self._get('categories'):
            if c['relationships']['parent']['data'] != None:
                data[c['id']] = c['attributes']['name']
        return data
    
    def accts(self):
        accts = self._get('accounts')
        if accts:
            data = {}
            for a in accts:
                data[a['id']] = {
                    'name': replace_emoji(a['attributes']['displayName'], replace='').lstrip(' '),
                    'role': 'savingAsset' if a['attributes']['accountType'] == 'SAVER' else 'defaultAsset',
                    'balance': a['attributes']['balance']['value']
                }
            return data
    
    def trans(self, data):
        try:
            r = get(data['relationships']['transaction']['links']['related'], headers=self._h)
            r.raise_for_status()
            return r.json()['data']
        except RequestException:
            print(r.text)
        
class Firefly(API):
    def __init__(self, token, url):
        super().__init__(token, url, 'about')
        self.queue = []
        Thread(target=self._add_from_queue).start()
        
    def _add_from_queue(self):
        while True:
            if len(self.queue) > 0:
                if not self._trans_exists(self.queue[0]['internal_reference']):
                    self._create_trans(self.queue[0])
                self.queue.pop(0)
            sleep(0.1)
    
    def cats(self):
        data = []
        for c in self._get('categories'):
            data.append(c['attributes']['name'])
        return data
    
    def acct_id(self, number):
        for a in self._get('accounts'):
            if a['attributes']['account_number'] == number:
                return a['id']
 
    def acct_name(self, id):
        try:
            acct = self._get(f'search/accounts?query={id}&field=number')[0]
            return acct['attributes']['name'] if id == acct['attributes']['account_number'] else None
        except:
            return None
        
    def rename_acct(self, id, new_name):
        self._put(f'accounts/{id}', {'name': new_name})
    
    def trans(self, id):
        return self._get(f'tags/{id}/transactions')[0]
    
    def _trans_exists(self, ref):
        try:
            return True if ref == self._get(f'search/transactions?query=internal_reference_is:{ref}')[0]['attributes']['transactions'][0]['internal_reference'] else False
        except:
            return False
        
    def create_acct(self, data):
        data['type'] = 'asset'
        data['currency_code'] = 'AUD'
        data['opening_balance_date'] = datetime.now().strftime('%Y-%m-%d')
        self._post('accounts', data)
    
    def _create_trans(self, data):
        self._post('transactions', {'transactions': [data]})
        
    def settle_trans(self, id):
        trans = self.trans(id)['attributes']['transactions'][0]
        if trans:
            p = {'transactions': [{
                'description': trans['description'].lstrip('[HELD] '),
                'source_name': trans['source_name']
            }]}
            self._put(f'transactions/{id}', p)
        
    def delete_trans(self, id):
        self._delete(f'transactions/{id}')
    
    def add_cat(self, name):
        self._post('categories', {'name': name})

def main():
    def xstr(s):
        return '' if s is None else str(s)
    
    up = Up(getenv('UP_TOKEN'), getenv('WEBHOOK_URL'))
    ff = Firefly(getenv('FIREFLY_TOKEN'), getenv('FIREFLY_URL'))
      
    # Check connection
    if not up.ping():
        print('Unable to connect to UP.')
    if not ff.ping():
        print('Unable to connect to Firefly.')
    if not up.wh_exists():
        up.create_wh()
    
    # Create accounts
    accts = up.accts()
    for a in accts:
        name = ff.acct_name(a)
        if not name:
            data = {}
            data['account_number'] = a
            data['name'] = accts[a]['name']
            data['account_role'] = accts[a]['role']
            data['opening_balance'] = accts[a]['balance']
            ff.create_acct(data)
        elif accts[a]['name'] != name:
            ff.rename_acct(ff.acct_id(a), accts[a]['name'])

    # Create categories
    up_cats = up.cats()
    ff_cats = ff.cats()
    for c in up_cats:
        if up_cats[c] not in ff_cats:
            ff.add_cat(up_cats[c])
    
    # Listen for webhooks
    app = Flask(__name__)
    @app.route('/', methods=['POST'])
    def respond():
        data = request.json['data']
        event = data['attributes']['eventType']
        trans = up.trans(data)
        
        if event == 'TRANSACTION_DELETED':
            ff.delete_trans(ff.trans(trans['id'])['id'])
        
        elif event == 'TRANSACTION_SETTLED':
            ff.settle_trans(ff.trans(trans['id'])['id'])
            
        elif event == 'TRANSACTION_CREATED':
            acct = accts[trans['relationships']['account']['data']['id']]['name']
            amnt = float(trans['attributes']['amount']['value'])
            text = xstr(trans['attributes']['rawText'])
            name = accts[trans['relationships']['account']['data']['id']]['name']
            desc = trans['attributes']['description']
            tags = ['FireUp']
            d = {}

            if not trans['relationships']['transferAccount']['data']:
                if amnt > 0:
                    d['type'] = 'deposit'
                    d['source_name'] = desc
                    d['destination_name'] = name
                elif amnt < 0:
                    d['type'] = 'withdrawal'
                    d['source_name'] = name
                    d['destination_name'] = desc
            
            else:
                if desc.startswith('Quick save transfer to') or desc.startswith('Transfer to'):
                    return Response(status=200)
                elif desc.startswith('Quick save transfer from'):
                    text = 'Quick Save'
                elif desc.startswith('Transfer from'):
                    text = 'Transfer'
                elif desc == 'Round Up':
                    text = 'Round Up'
                elif desc.startswith('Cover from'):
                    text = 'Cover'
        
                d['type'] = 'transfer'
                d['source_name'] = accts[trans['relationships']['transferAccount']['data']['id']]['name']
                d['destination_name'] = acct

                tags.append(text)
                desc = '[HELD] ' + text if trans['attributes']['status'] == 'HELD' else text
                msg = xstr(trans['attributes']['message'])
                if msg:
                    if text:
                        msg = f'({msg})'
                    desc = f'{desc} {msg}'
                if trans['attributes']['foreignAmount']:
                    foreign_amnt = trans['attributes']['foreignAmount']['value'] + ' ' + trans['attributes']['foreignAmount']['currencyCode']
                    desc = f'{desc} {foreign_amnt}'

            d['internal_reference'] = trans['id']
            d['description'] = desc
            d['category_name'] = up_cats[trans['relationships']['category']['data']['id']] if trans['relationships']['category']['data'] else None
            d['tags'] = tags
            d['date'] = trans['attributes']['createdAt']
            d['amount'] = str(abs(amnt))      
 
            ff.queue.append(d)
        
        return Response(status=200)
            
    print('Ready to accept incoming connections')
    serve(app, host='0.0.0.0', port=int(getenv('PORT')))

if __name__ == '__main__':
    main()