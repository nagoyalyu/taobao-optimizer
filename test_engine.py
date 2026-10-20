from engine import extract_page,calculate,suggest_thresholds
from fetcher import allowed_url

def item(price=500,shop='A',activity='X'):
 return {'name':'x','price':price,'shop':shop,'activity':activity,'qty':1,'confirmed':True}
def rule(scope='platform',target='',threshold=700,off=100):
 return {'name':'券','scope':scope,'target':target,'threshold':threshold,'off':off,'confirmed':True,'stage':2}
def test_platform():
 res=calculate([item(500),item(250,'B')],[rule()]);assert res['pay']==650
def test_activity_scope():
 res=calculate([item(500),item(250,'B','Y')],[rule('activity','X')]);assert res['pay']==750
def test_shop_scope():
 res=calculate([item(500),item(250,'B')],[rule('shop','A',500,50)]);assert res['pay']==700
def test_exclusive():
 a=rule(threshold=0,off=100);b=rule(threshold=0,off=80);a['exclusive_group']='g';b['exclusive_group']='g';assert calculate([item(500)],[a,b])['pay']==400
def test_page():
 v=extract_page('<title>耳机</title><p>原价¥899 现价¥799 满800减80</p>','https://item.taobao.com/item.htm?id=12345678');assert v['original_candidates']==[899];assert v['current_candidates']==[799];assert v['item_id']=='12345678';assert not v['rules'][0]['verified']
def test_allow():
 assert allowed_url('https://item.taobao.com/item.htm?id=1000000');assert not allowed_url('https://taobao.com.evil.com/');assert not allowed_url('http://item.taobao.com/')
def test_unconfirmed():
 try:calculate([{**item(),'confirmed':False}],[]);assert False
 except ValueError:pass
