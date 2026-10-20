import requests
from urllib.parse import urlparse
from engine import extract_page
ALLOW=('taobao.com','tmall.com','detail.tmall.com')
HEADERS={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Accept-Language':'zh-CN,zh;q=0.9'}
def allowed_url(url):
    try:
        p=urlparse(url.strip())
        h=(p.hostname or '').lower()
        return p.scheme=='https' and any(h==d or h.endswith('.'+d) for d in ALLOW) and not p.username and not p.password
    except ValueError:return False

def public_fetch(url):
    if not allowed_url(url):return {'url':url,'status':'invalid_url','error':'仅允许 https 的淘宝和天猫商品页，不会访问其他主机。'}
    try:
        # requests automatic redirect disabled to prevent arbitrary off-domain requests
        r=requests.get(url,headers=HEADERS,timeout=(5,12),allow_redirects=False)
        if r.status_code in (301,302,303,307,308):
            return {'url':url,'status':'redirect','error':'页面重定向，避免访问未经验证的域名；请粘贴最终淘宝商品链接。'}
        if r.status_code!=200:return {'url':url,'status':'blocked','error':f'HTTP {r.status_code}：网页不可公开访问或被访问限制。'}
        if len(r.content)>3_000_000:return {'url':url,'status':'oversized','error':'页面超过安全大小限制。'}
        parsed=extract_page(r.text,url)
        if not parsed['current_candidates'] and not parsed['original_candidates']:
            parsed['status']='partial';parsed['warnings'].append('商品价格可能由动态接口加载、需登录或者页面受限。')
        else:parsed['status']='parsed_unverified'
        return parsed
    except requests.RequestException as e:
        return {'url':url,'status':'failed','error':type(e).__name__+': '+str(e)[:160]}
