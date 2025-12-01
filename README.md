# DigitalPlat Domain Auto-Renew 自动续期脚本  
**全自动帮你登录 DigitalPlat（DigitalPlat.org / dp.la）并续期域名，完全免费，每 3 天自动执行一次，支持 Telegram 消息推送**

## 效果演示
部署成功后，你会收到类似这样的 Telegram 消息：
```
✅ DigitalPlat 检查完毕！
已成功续期 3 个域名：
example.com 续期至 2026-12-31
test.org 续期至 2026-12-31
abc.net 续期至 2026-12-31
```
## 一键部署（零基础也能 3 分钟搞定）

### 第一步：Fork 本仓库
点击右上角 `Fork` 按钮，把仓库叉到你自己的 GitHub 账号下。

### 第二步：添加 Secrets（最重要的步骤！）

1. 进入你 Fork 后的仓库 → 点击上方 **Settings**  
2. 左侧菜单找到 **Secrets and variables** → **Actions**  
3. 点击绿色按钮 **New repository secret**，按下面顺序依次添加（共 5 个，缺一不可的前四个）：

| 序号 | Name（名称必须完全一致） | Secret Value（填什么）                          | 是否必填 |
|------|--------------------------|--------------------------------------------------|----------|
| 1    | `DP_EMAIL`              | 你的 DigitalPlat 登录邮箱                         | 必填     |
| 2    | `DP_PASSWORD`           | 你的 DigitalPlat 登录密码                         | 必填     |
| 3    | `TG_BOT_TOKEN`          | 你的 Telegram Bot Token（如 `123456:ABC-defGhIJKlMnOPrStUvWxYZ`） | 必填     |
| 4    | `TG_CHAT_ID`            | 你的 Telegram 个人用户 ID（纯数字，例如 `987654321`） | 必填     |
| 5    | `BARK_KEY`              | Bark 推送 Key（没有就不填，留空即可）            | 可选     |

> Tips：  
> - Telegram Bot Token 找 @BotFather 创建机器人即可获得  
> - 你的 Chat ID 可以私聊 @userinfobot 立刻获取

### 第三步：手动跑一次测试
1. 点击仓库上方的 **Actions** 标签  
2. 左侧选中 workflow **DigitalPlat Domain Renew**  
3. 右侧点击 **Run workflow** → 绿色 **Run workflow**  
4. 等待 10~30 秒，刷新页面点进任务日志  
5. 如果看到绿色的 √ 和 `成功续期 X 个域名`，说明全部配置正确！  
6. 同时你的 Telegram 会收到第一条续期成功的消息

### 第四步：坐等自动续期
默认已设置 **每天运行一次**（实际脚本内部会自动判断是否需要续期，只有快到期的才会真续），完全无人值守。  
以后每 3 天会自动帮你续期一次，再也不用担心域名被回收！

## 常见问题 Q&A
**Q：会不会泄露密码？**  
A：密码只以 GitHub 加密 Secret 形式存储，只有 GitHub Actions 运行时才能解密读取，源码里完全看不到明文，放心使用。

**Q：支持多个账号吗？**  
A：支持！在 Secrets 里用逗号分隔邮箱和密码即可（脚本已内置多账号逻辑），例如：  
`DP_EMAIL` = `a@example.com,b@example.com`  
`DP_PASSWORD` = `pass123,pass456`

**Q：我想改成每天推送一次状态？**  
A：直接编辑 `.github/workflows/renew.yml` 文件，把 `schedule` 的 `cron` 改成你想要的时间即可。

## Star & 分享
觉得好用请给个 Star ✨ 你的支持就是我更新的动力～

有问题直接提 Issue，我看到都会秒回！
