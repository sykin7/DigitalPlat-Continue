import os
import sys
import asyncio
import requests
import random
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 环境变量配置 ---
DP_EMAIL = os.getenv("DP_EMAIL")
DP_PASSWORD = os.getenv("DP_PASSWORD")

# 通知配置 (Bark & Telegram)
BARK_KEY = os.getenv("BARK_KEY")
BARK_SERVER = os.getenv("BARK_SERVER", "https://api.day.app")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# --- 常量定义 ---
LOGIN_URL = "https://dash.domain.digitalplat.org/auth/login"
DOMAINS_URL = "https://dash.domain.digitalplat.org/panel/main?page=%2Fpanel%2Fdomains"
TIMEOUTS = {
    "page_load": 60000,
    "element_wait": 30000,
    "navigation": 60000,
    "login_wait": 180000
}

def validate_config():
    """检查必要的登录凭据"""
    if not DP_EMAIL or not DP_PASSWORD:
        logger.error("配置错误: 缺少 DP_EMAIL 或 DP_PASSWORD。")
        send_notification("DigitalPlat 配置错误", "缺少必要的登录环境变量，脚本停止运行。")
        sys.exit(1)

def send_notification(title, body, level="active"):
    """统一发送通知 (Bark + Telegram)"""
    logger.info(f"正在发送通知: {title}")
    
    # 1. 发送 Bark 通知
    if BARK_KEY:
        try:
            api_url = f"{BARK_SERVER.rstrip('/')}/{BARK_KEY}"
            payload = {
                "title": title,
                "body": body,
                "group": "DigitalPlat Renew",
                "level": level
            }
            requests.post(api_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Bark 发送失败: {e}")

    # 2. 发送 Telegram 通知
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            tg_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            # Telegram 不支持复杂的 level 参数，直接发送文本
            text_content = f"*{title}*\n\n{body}"
            payload = {
                "chat_id": TG_CHAT_ID,
                "text": text_content,
                "parse_mode": "Markdown"
            }
            requests.post(tg_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Telegram 发送失败: {e}")

def save_results(renewed_domains, failed_domains):
    results = {
        "timestamp": datetime.now().isoformat(),
        "renewed_count": len(renewed_domains),
        "failed_count": len(failed_domains),
        "renewed_domains": renewed_domains,
        "failed_domains": failed_domains
    }
    try:
        with open("renewal_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存结果失败: {e}")

async def simulate_human_behavior(page):
    await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
    await asyncio.sleep(random.uniform(0.5, 2))

async def setup_browser(playwright):
    browser = await playwright.firefox.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-gpu']
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        viewport={"width": 1920, "height": 1080}
    )
    return browser, context

async def login(page):
    logger.info("开始登录流程...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUTS["page_load"])
    await simulate_human_behavior(page)

    # 等待人机验证自动跳转
    try:
        await page.wait_for_selector("input[name='email']", timeout=TIMEOUTS["login_wait"])
    except PlaywrightTimeoutError:
        error_msg = "登录超时: 无法跳过人机验证"
        logger.error(error_msg)
        await page.screenshot(path="login_timeout.png")
        send_notification("DigitalPlat 登录失败", "无法跳过 Cloudflare 验证，请检查截图。")
        raise Exception(error_msg)

    # 输入凭据
    await page.type("input[name='email']", DP_EMAIL, delay=random.randint(50, 150))
    await page.type("input[name='password']", DP_PASSWORD, delay=random.randint(50, 150))
    
    async with page.expect_navigation(wait_until="networkidle", timeout=TIMEOUTS["navigation"]):
        await page.click("button[type='submit']")

    if "/panel/main" not in page.url:
        await page.screenshot(path="login_failed.png")
        raise Exception("登录失败: 未跳转至仪表盘")
    
    logger.info("登录成功")

async def process_domain(page, domain_name, domain_url_path, base_url):
    try:
        full_url = base_url + domain_url_path
        logger.info(f"正在检查域名: {domain_name}")
        await page.goto(full_url, wait_until="networkidle", timeout=TIMEOUTS["navigation"])

        renew_link = page.locator("a[href*='renewdomain']")
        if await renew_link.count() == 0:
            logger.info(f"{domain_name}: 无需续期")
            return None, None

        logger.info(f"{domain_name}: 发现续期链接，开始处理...")
        async with page.expect_navigation(timeout=TIMEOUTS["navigation"]):
            await renew_link.click()

        # 点击 Order Now / Continue
        btn = page.locator("button:has-text('Order Now'), button:has-text('Continue')").first
        if await btn.count() > 0:
            async with page.expect_navigation(timeout=TIMEOUTS["navigation"]):
                await btn.click()
            
            # 勾选协议
            tos = page.locator("input[name='accepttos']")
            if await tos.count() > 0:
                await tos.check()
            
            # 结账
            checkout = page.locator("button#checkout")
            if await checkout.count() > 0:
                async with page.expect_navigation(timeout=TIMEOUTS["navigation"]):
                    await checkout.click()
                
                content = await page.inner_text("body")
                if "Order Confirmation" in content or "successfully" in content.lower():
                    logger.info(f"{domain_name}: 续期成功")
                    return True, None
                else:
                    return False, f"{domain_name} (确认失败)"
            return False, f"{domain_name} (无结账按钮)"
        return False, f"{domain_name} (无下单按钮)"

    except Exception as e:
        logger.error(f"{domain_name} 异常: {e}")
        return False, f"{domain_name} (异常: {str(e)})"

async def main():
    validate_config()
    renewed = []
    failed = []

    async with async_playwright() as p:
        browser, context = await setup_browser(p)
        page = await context.new_page()
        
        # 反检测脚本
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            await login(page)
            
            await page.goto(DOMAINS_URL, wait_until="networkidle")
            await page.wait_for_selector("table.table-domains", timeout=TIMEOUTS["element_wait"])
            
            rows = await page.locator("table.table-domains tbody tr").all()
            base_url = "https://dash.domain.digitalplat.org/"
            
            logger.info(f"发现 {len(rows)} 个域名")
            
            for row in rows:
                onclick = await row.get_attribute("onclick")
                if onclick:
                    path = onclick.split("'")[1]
                    name = await row.locator("td:nth-child(1)").inner_text()
                    
                    is_success, error = await process_domain(page, name.strip(), path, base_url)
                    if is_success:
                        renewed.append(name.strip())
                    elif error:
                        failed.append(error)
                    
                    await page.goto(DOMAINS_URL, wait_until="networkidle")

            # 最终通知
            if renewed or failed:
                msg = ""
                if renewed:
                    msg += f"✅ 成功: {len(renewed)}\n" + "\n".join(renewed) + "\n\n"
                if failed:
                    msg += f"❌ 失败: {len(failed)}\n" + "\n".join(failed)
                send_notification("DigitalPlat 续期报告", msg.strip())
            else:
                logger.info("无域名需要续期")
                send_notification("DigitalPlat 检查完毕", "所有域名状态正常，无需续期。", level="passive")

            save_results(renewed, failed)

        except Exception as e:
            logger.critical(f"脚本严重错误: {e}")
            send_notification("DigitalPlat 运行出错", str(e))
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
