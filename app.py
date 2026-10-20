import json
import pandas as pd
import streamlit as st
from engine import extract_page,calculate,suggest_thresholds
from fetcher import public_fetch
st.set_page_config(page_title='淘宝三阶段优惠核算',page_icon='🛒',layout='wide')
st.title('🛒 淘宝 · 三阶段优惠核算 V3')
st.caption('商品页读取 → 店铺/跨店活动核验 → 平台优惠叠加与购物车计算 | 非淘宝官方工具')
st.warning('没有获得完整的淘宝优惠接口和账户授权，无法保证自动取得所有实时价格、店铺活动、平台券。抓取结果都是候选证据，必须确认后才能计算。')
if 'pages' not in st.session_state:st.session_state.pages=[]
if 'items' not in st.session_state:st.session_state.items=[]
if 'rules' not in st.session_state:st.session_state.rules=[]
page1,page2,page3=st.tabs(['① 链接抓取与价格','② 店铺和跨店满减','③ 平台券与全车最优'])
with page1:
    st.subheader('批量输入商品链接')
    links=st.text_area('每行一个淘宝/天猫 HTTPS 商品链接',height=115,placeholder='https://item.taobao.com/item.htm?id=...')
    if st.button('实际访问公开商品页并提取',type='primary'):
        urls=list(dict.fromkeys(x.strip() for x in links.splitlines() if x.strip()))
        if len(urls)>15:st.error('一次最多15个链接')
        else:
            results=[]
            with st.spinner('抓取公开商品页中…'):
                for u in urls:results.append(public_fetch(u))
            st.session_state.pages=results
    st.markdown('**抓取结果与证据**')
    for ix,p in enumerate(st.session_state.pages):
        with st.expander(f"{ix+1}. {p.get('title') or p.get('url','未知')} — {p.get('status','unknown')}",expanded=ix==0):
            st.write('链接：',p.get('url'))
            if p.get('error'):st.error(p['error'])
            else:
                st.write('原价候选：',p.get('original_candidates',[]),'｜现价候选：',p.get('current_candidates',[]))
                st.write('页面提到的满减（适用范围未确认）：',p.get('rules',[]))
                for w in p.get('warnings',[]):st.info(w)
    st.divider()
    st.subheader('浏览器已登录？可导入自己保存的商品页 HTML')
    st.caption('在淘宝商品页使用浏览器“网页另存为 HTML”，上传到这里；程序只分析你自己上传的文件，不读取 Cookie。动态渲染和选规格后的价格可能依旧缺失。')
    htmls=st.file_uploader('上传HTML（支持多个）',type=['html','htm'],accept_multiple_files=True)
    if st.button('分析上传的HTML'):
        for f in htmls or []:
            data=f.read()
            if len(data)>3_000_000:st.error(f'{f.name} 超过3MB');continue
            parsed=extract_page(data.decode('utf-8',errors='replace'),f.name);parsed['status']='user_uploaded_unverified'
            st.session_state.pages.append(parsed)
        st.rerun()
    st.divider()
    st.subheader('确认后纳入购物车')
    st.caption('只有原价和现价确实来自商品页且规格一致时才勾选“价格已核对”。')
    with st.form('new_item',clear_on_submit=True):
        suggestions=[p for p in st.session_state.pages if not p.get('error')]
        source=st.selectbox('抓取来源',options=['手工添加']+[f"{i+1}: {p.get('title') or p.get('url','')[:50]}" for i,p in enumerate(suggestions)])
        a,b,c=st.columns(3)
        name=a.text_input('商品名称和规格');shop=b.text_input('店铺名称');price=c.number_input('实际单价/现价（元）',min_value=0.0,step=1.0,format='%.2f')
        d,e,f=st.columns(3)
        original=d.number_input('原价/标价（元，可不填）',min_value=0.0,step=1.0);qty=e.number_input('数量',min_value=1,max_value=100,value=1);activity=f.text_input('跨店活动组（需核实，例：同一活动A）')
        link=st.text_input('商品链接');confirmed=st.checkbox('我已在淘宝商品页核对现价、规格、店铺和数量')
        if st.form_submit_button('加入购物车'):
            if not name or not shop or not confirmed:st.error('须填写商品和店铺，并确认价格')
            else:
                if source!='手工添加':
                    chosen=suggestions[int(source.split(':')[0])-1]
                    link=link or chosen.get('url','')
                st.session_state.items.append({'name':name,'shop':shop,'price':price,'original':original,'qty':qty,'activity':activity,'url':link,'confirmed':True})
                st.success('商品已加入')
    if st.session_state.items:
        st.dataframe(pd.DataFrame(st.session_state.items),hide_index=True,use_container_width=True)
        if st.button('清空商品'):st.session_state.items=[];st.rerun()
with page2:
    st.subheader('店铺/跨店优惠候选发现')
    st.info('商品页面出现“满N减M”只能证明页面写过这条文案，不能自动确认参与店铺、可用日期、门槛基准或能否叠加。请依据店铺活动页/结算页将确认后的优惠添加为规则。')
    for p in st.session_state.pages:
        for r in p.get('rules',[]):
            st.write(f"来自 {p.get('title') or p.get('url')}：满 {r['threshold']} 减 {r['off']}，上下文：{r['evidence']}")
    shops=sorted({x['shop'] for x in st.session_state.items})
    groups=sorted({x['activity'] for x in st.session_state.items if x['activity']})
    st.write('当前商品涉及店铺：',', '.join(shops) or '尚无')
    st.write('已确认的跨店活动组：',', '.join(groups) or '尚无')
    st.caption('活动组相同的商品可以在优化器内合计达到门槛；不同店铺之间不自动假设能跨店。')
with page3:
    st.subheader('录入已确认的优惠条件')
    st.caption('店铺券、跨店活动及平台券都属于规则。请从公开官方说明或实际券详情/结算页面确认后再勾选。')
    with st.form('add_rule',clear_on_submit=True):
        x,y,z=st.columns(3)
        rn=x.text_input('规则名称',placeholder='双十一平台券 满1000减100')
        scope=y.selectbox('作用范围',['shop','activity','platform'],format_func=lambda x:{'shop':'单店','activity':'同一跨店活动组','platform':'全车平台'}[x])
        target=z.text_input('店名/跨店活动组（全平台留空）')
        v1,v2,v3=st.columns(3)
        threshold=v1.number_input('门槛元',min_value=0.,step=10.);off=v2.number_input('减免元',min_value=0.,step=1.);stage=v3.selectbox('计算层级',[1,2,3],help='1店铺/单品，2跨店/平台，3红包/支付；若平台采用平行满减，需另行核验')
        v4,v5=st.columns(2)
        exclusive=v4.text_input('互斥组',placeholder='例如 店铺A券和满折择优')
        repeat=v5.checkbox('每满一次可重复减免')
        confirmed_rule=st.checkbox('已确认生效时段、适用店铺/商品、叠加及门槛规则')
        if st.form_submit_button('添加优惠规则'):
            if not rn or (scope!='platform' and not target) or off<=0 or (threshold>0 and off>threshold) or not confirmed_rule:st.error('请检查规则并确认所有条件')
            else:
                st.session_state.rules.append({'name':rn,'scope':scope,'target':target,'threshold':threshold,'off':off,'stage':stage,'exclusive_group':exclusive,'repeat':repeat,'confirmed':True})
                st.success('规则已添加')
    if st.session_state.rules:
        st.dataframe(pd.DataFrame(st.session_state.rules),hide_index=True,use_container_width=True)
        if st.button('清空规则'):st.session_state.rules=[];st.rerun()
    if st.session_state.items and st.session_state.rules:
        st.subheader('哪些优惠达到门槛，差多少钱？')
        st.dataframe(pd.DataFrame(suggest_thresholds(st.session_state.items,st.session_state.rules)),hide_index=True,use_container_width=True)
    if st.button('计算全购物车最低实付',type='primary'):
        if not st.session_state.items:st.error('先导入并确认商品')
        else:
            try:
                best=calculate(st.session_state.items,st.session_state.rules)
                st.metric('已确认规则下的最低实付（单笔合单模型）',f"¥{best['pay']:,.2f}",delta=f"节省 ¥{best['saved']:,.2f}",delta_color='normal')
                st.write('基准价：',best['base'],'元')
                if best['applied']:st.dataframe(pd.DataFrame(best['applied']),hide_index=True)
                else:st.info('当前没有能进一步减价的确认优惠。')
                st.caption('不能据此保证淘宝支付页相同金额：本模型假设按设置的阶段顺序计算、适用范围可按订单金额分摊，且只优化当前选定商家的一笔合单；没有模拟复杂拆单、券资产、平行满减、运费和支付渠道。')
            except Exception as e:st.error(str(e))
    export=json.dumps({'items':st.session_state.items,'rules':st.session_state.rules,'pages':st.session_state.pages},ensure_ascii=False,indent=2)
    st.download_button('下载购物车、规则与抓取证据 JSON',data=export,file_name='taobao_cart_evidence.json',mime='application/json')
st.divider()
st.caption('隐私：公开抓取不要求淘宝账号密码；切勿上传Cookie、账号凭证、订单隐私。不要将抓取到的广告划线价误作成交原价。')
