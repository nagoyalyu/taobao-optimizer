"""Conservative rule parser and cart optimizer; no fabricated discounts."""
import re
import itertools
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

def yuan(x):
    return int((Decimal(str(x))*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def extract_id(link):
    m=re.search(r'(?:[?&](?:id|itemId|item_id)=|/item/)(\d{6,})',link,re.I)
    return m.group(1) if m else ''

def extract_page(html, url=''):
    soup=BeautifulSoup(html,'html.parser')
    for node in soup(['script','style','noscript']): node.decompose()
    text=' '.join(soup.stripped_strings)
    title=(soup.title.get_text(' ',strip=True) if soup.title else '')[:140]
    # Never treat struck-through original price or arbitrary page numbers as a checkout price.
    original_patterns=[r'(?:划线价|原价|专柜价|市场价)\s*[¥￥]?\s*(\d[\d,]*(?:\.\d{1,2})?)']
    current_patterns=[r'(?:到手价|券后价|活动价|促销价|现价)\s*[¥￥]?\s*(\d[\d,]*(?:\.\d{1,2})?)']
    def find(patterns):
        out=[]
        for p in patterns:
            for m in re.finditer(p,text,re.I):
                try:
                    v=float(m.group(1).replace(',',''))
                    if 0 < v < 10000000: out.append(round(v,2))
                except ValueError:pass
        return list(dict.fromkeys(out))[:10]
    orig=find(original_patterns); now=find(current_patterns)
    warnings=[]
    if len(now)!=1: warnings.append('页面没有唯一、明确标注的现价；不能可靠自动确定付款金额。')
    if len(orig)!=1: warnings.append('页面没有唯一明确的原价；不以划线价推算折扣。')
    rules=[]
    patterns=[('full',r'(?:满)\s*(\d{2,7}(?:\.\d{1,2})?)\s*(?:元)?\s*(?:减|立减)\s*(\d{1,7}(?:\.\d{1,2})?)'),('every',r'(?:每满)\s*(\d{2,7}(?:\.\d{1,2})?)\s*(?:元)?\s*(?:减)\s*(\d{1,7}(?:\.\d{1,2})?)')]
    for kind,pat in patterns:
        for m in re.finditer(pat,text):
            threshold=float(m.group(1)); off=float(m.group(2))
            if off>=threshold:continue
            evidence=text[max(0,m.start()-65):min(len(text),m.end()+75)]
            rules.append({'type':'fixed','threshold':threshold,'off':off,'repeat':kind=='every','evidence':evidence,'scope':'未确认','verified':False})
    return {'url':url,'item_id':extract_id(url),'title':title,'original_candidates':orig,'current_candidates':now,'rules':rules[:25],'warnings':warnings,'source':'public_html','raw_text_excerpt':text[:600]}

def benefit(eligible, rule):
    threshold=yuan(rule.get('threshold',0)); off=yuan(rule.get('off',0))
    if eligible<threshold or eligible<=0: return 0
    if rule.get('type','fixed')=='rate':
        return min(eligible, round(eligible*float(rule.get('off',0))/100))
    return min(eligible,off*(eligible//threshold if threshold and rule.get('repeat') else 1))

def calculate(rows, rules, cap=350000):
    """Enumerate validated stage-ordered promotions, allocation, and store subsets.
    rows: item_id/shop/price/qty/activity. rules: shop/activity/platform scopes;
    stages ordered. Multiple discounts with same exclusive_group cannot stack.
    Designed for one checkout group, does not assert Taobao's own allocation policy.
    """
    if len(rules)>15:raise ValueError('优惠规则超过15条，请先筛选。')
    if len(rows)>16:raise ValueError('单次最多16件商品行。')
    if any(not r.get('confirmed') for r in rows):raise ValueError('存在未确认商品价格，无法给出可信总价。')
    if any(not r.get('confirmed') for r in rules):raise ValueError('存在未确认优惠叠加规则，无法给出可信总价。')
    total_steps=1<<len(rules)
    if total_steps>cap:raise ValueError('组合太多')
    base=[yuan(r['price'])*int(r.get('qty',1)) for r in rows]
    if any(x<0 for x in base):raise ValueError('价格不能为负数')
    ordered=sorted(enumerate(rules),key=lambda x:(int(x[1].get('stage',2)),x[0]))
    best=None
    for mask in range(total_steps):
        rem=base[:]; applied=[]; group_set=set(); valid=True
        for ix,r in ordered:
            if not (mask&(1<<ix)):continue
            group=r.get('exclusive_group','')
            if group and group in group_set:valid=False;break
            if group:group_set.add(group)
            scope=r.get('scope','platform');target=r.get('target','')
            indices=[i for i,row in enumerate(rows) if scope=='platform' or (scope=='shop' and row.get('shop')==target) or (scope=='activity' and target and row.get('activity')==target)]
            eligible=sum(rem[i] for i in indices)
            disc=benefit(eligible,r)
            if not disc or not indices:valid=False;break
            alloc=[disc*rem[i]//eligible for i in indices]
            leftover=disc-sum(alloc)
            for j in range(leftover): alloc[j%len(alloc)]+=1
            for i,d in zip(indices,alloc):rem[i]-=d
            applied.append({'name':r.get('name','优惠'),'saved':disc/100,'scope':scope})
        if not valid:continue
        pay=sum(rem)
        if best is None or pay<best['pay_cents']:
            best={'pay_cents':pay,'pay':pay/100,'base':sum(base)/100,'saved':(sum(base)-pay)/100,'applied':applied,'remaining':[v/100 for v in rem]}
    return best

def suggest_thresholds(rows,rules):
    suggestions=[]
    for r in rules:
        scope=r.get('scope','platform');target=r.get('target','')
        eligible=sum(yuan(x['price'])*int(x.get('qty',1)) for x in rows if scope=='platform' or scope=='shop' and x.get('shop')==target or scope=='activity' and target and x.get('activity')==target)/100
        gap=round(max(0,float(r.get('threshold',0))-eligible),2)
        suggestions.append({'name':r.get('name','优惠'),'scope':scope,'target':target,'eligible':round(eligible,2),'gap':gap,'condition_met':gap==0,'note':'这是优惠前门槛的预检查；实际可能依据叠加层级调整。'})
    return suggestions
