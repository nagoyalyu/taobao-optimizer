# 淘宝三阶段优惠核算 V3

## 解决的问题
1. **商品链接自动尝试访问**：逐条发起真实 HTTP 请求，提取页面明确标记的原价/现价候选值和“满 X 减 Y”线索。结果显示 `parsed_unverified` / `partial` / `blocked` 等状态。由于淘宝价格经常在动态接口/登录后才展示，不能保证每条链接都抓到；绝不凭链接捏造价格。
2. **店铺与跨店活动**：保存店铺标识和已确认的跨店活动组，列出找到的满减文案供核对，逐条将确认过的满减添加成规则。实现按作用范围判断门槛、差额提醒。
3. **平台优惠与结算**：以已确认的价格和规则组合为输入，穷举优惠券组合，按阶段从小到大计算分摊优惠和互斥组。输出最低**单次合单**实付金额与明细。

## 重要限制
- 没有淘宝开发者 AppKey/Secret 和对应场景权限，无法调用需签名的淘宝开放平台 API。即使有权限，也不保证得到所有消费者个性化 88VIP、支付及店铺隐藏券。
- 此版不是全自动“输入链接就得出准确到手价”。商品详情可能要求登录、JavaScript 动态加载或只在 App 展示。解析器保守提取明确标价和满减文本；要求人工在结算页核实。登录态页面可自行使用浏览器“另存为 HTML”上传到网站分析，不提供 Cookie。
- 本版只能优化一笔合单的已确认优惠组合；**尚不支持自动拆单、自动匹配其他商家、自动抓取店铺全部活动、自动从淘宝平台活动首页同步双十一所有规则**。不要把它当淘宝最终支付价。部分2026店铺满减/满件和店铺券可能互斥，务必写入同一个互斥组。
- 当前是单用户会话工具，没有账户数据库。不要向公开部署上传个人身份资料或私密订单。

## 用浏览器部署，不需自己安装 Python
1. 将目录上传到 GitHub 仓库（从 GitHub Web UI 上传文件），不要上传任何账户密钥。
2. 访问 https://dashboard.render.com/ 新建 Web Service，选择该 GitHub 仓库。仓库自带 `Dockerfile` 与 `render.yaml`；如果不走 Blueprint，可选择 Docker Runtime 部署。
3. 发布后会得到 `https://...onrender.com` 地址。平台是否有免费额度，以实际报价为准。

你也可使用 Streamlit Community Cloud 部署：在 GitHub 上传文件，访问 https://share.streamlit.io/，选择 `app.py` 发布。

## 本地运行（非必需）
`pip install -r requirements.txt`
`streamlit run app.py`
`pytest -q`

## 官方API升级
参考 https://developer.alibaba.com/docs/api.htm?apiId=46283 和 https://developer.alibaba.com/docs/api.htm?apiId=28111。已有接口可以查询部分商品及淘宝客券，但要有已申请的 AppKey、签名、相应 PID 或业务授权，接口覆盖和权限因场景不同。不可在浏览器前端暴露 Secret。
